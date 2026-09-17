"""Gmail sending through Google's OAuth + REST API, with no browser UI involved.

This module only talks to Google's documented OAuth2 and Gmail API v1
endpoints over HTTPS (stdlib `urllib`). It never drives a browser: the one
place a browser is needed is the interactive consent screen, which the
caller drives separately and then hands the resulting authorization code (or
a cached refresh token) to the functions here.
"""
from __future__ import annotations

import base64
import json
import secrets
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import certifi

# Some Python installations (notably python.org's macOS installer without
# running Install Certificates.command) ship without a working default CA
# trust store, so plain urlopen() calls fail with CERTIFICATE_VERIFY_FAILED.
# The rest of this app already pins certifi's bundle for exactly this reason
# (see ensure_external_dependencies in main.py); do the same here.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
# Lets the userinfo endpoint return the account's actual display name (not
# just its email) so sent mail can show a real sender name instead of
# Gmail's own "text before @" fallback when a From header has no name part.
GOOGLE_PROFILE_SCOPE = "https://www.googleapis.com/auth/userinfo.profile"
GMAIL_SEND_AND_PROFILE_SCOPE = f"{GMAIL_SEND_SCOPE} {GOOGLE_PROFILE_SCOPE}"


class OAuthLoopbackServer:
    """Catches Google's OAuth redirect on 127.0.0.1 for one authorization.

    Google's OAuth desktop-app flow requires a loopback redirect URI (the
    out-of-band "copy this code" flow was retired in 2022), so completing
    sign-in means briefly running a local HTTP server to receive the single
    redirect Google sends back after the person clicks Allow.
    """

    def __init__(self) -> None:
        self._server = HTTPServer(("127.0.0.1", 0), _make_handler(self))
        self.port = self._server.server_port
        self.redirect_uri = f"http://127.0.0.1:{self.port}/"
        self.code: str | None = None
        self.error: str | None = None
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def _serve(self) -> None:
        while not self._done.is_set():
            self._server.handle_request()

    def start(self) -> "OAuthLoopbackServer":
        self._thread.start()
        return self

    def wait_for_code(self, timeout: float = 180.0) -> str:
        received = self._done.wait(timeout)
        self.stop()
        if not received:
            raise TimeoutError("Timed out waiting for Google sign-in to complete.")
        if self.error:
            raise RuntimeError(f"Google sign-in was cancelled or denied: {self.error}")
        if not self.code:
            raise RuntimeError("Google did not return an authorization code.")
        return self.code

    def stop(self) -> None:
        self._done.set()
        try:
            self._server.server_close()
        except Exception:
            pass


def _make_handler(server: "OAuthLoopbackServer"):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            server.code = (params.get("code") or [None])[0]
            server.error = (params.get("error") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            message = (
                "You can close this window and return to EzyMailer."
                if server.code
                else "Sign-in was cancelled. You can close this window."
            )
            self.wfile.write(
                f"<html><body style='font-family:sans-serif;padding:40px'>"
                f"<h2>{message}</h2></body></html>".encode("utf-8")
            )
            server._done.set()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    return Handler


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    *,
    scope: str = GMAIL_SEND_SCOPE,
    login_hint: str | None = None,
) -> tuple[str, str]:
    """Return (authorization_url, state) for a Google OAuth consent request."""
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}", state


def _post_form(url: str, fields: dict[str, str]) -> dict[str, Any]:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google OAuth request failed ({exc.code}): {detail}") from exc


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict[str, Any]:
    return _post_form(
        GOOGLE_TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    return _post_form(
        GOOGLE_TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )


def revoke_token(token: str) -> None:
    """Revoke a refresh (or access) token at Google, for a "Logout" action.

    This invalidates the grant on Google's side, not just the local copy —
    the account will show up again under "test users -> access removed" and
    any cached access token derived from it stops working immediately.
    """
    data = urllib.parse.urlencode({"token": token}).encode("utf-8")
    request = urllib.request.Request(
        GOOGLE_REVOKE_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15, context=_SSL_CONTEXT) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google token revocation failed ({exc.code}): {detail}") from exc


def fetch_account_profile(access_token: str) -> dict[str, str]:
    """Best-effort lookup of the signed-in account's email and display name.

    Needs the userinfo.profile scope (see GMAIL_SEND_AND_PROFILE_SCOPE) in
    addition to gmail.send — a token authorized before that scope existed
    simply gets {} back here instead of an error, and the caller falls back
    to sending with no display name (Gmail then shows the "text before @"
    fallback in the recipient's inbox, exactly as before this existed).
    """
    request = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15, context=_SSL_CONTEXT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return {}
    return {"email": str(payload.get("email") or ""), "name": str(payload.get("name") or "")}


def _build_mime_message(
    sender_email: str,
    sender_name: str,
    to: str,
    subject: str,
    body_text: str,
    html_body: str | None,
    attachment_paths: list[Path],
) -> bytes:
    from email.utils import formataddr

    message = MIMEMultipart("mixed")
    message["To"] = to
    message["From"] = formataddr((sender_name, sender_email)) if sender_name else sender_email
    message["Subject"] = subject

    if html_body:
        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(body_text or "", "plain"))
        alternative.attach(MIMEText(html_body, "html"))
        message.attach(alternative)
    else:
        message.attach(MIMEText(body_text or "", "plain"))

    for path in attachment_paths:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
        message.attach(part)

    return message.as_bytes()


def send_message(
    access_token: str,
    sender: str,
    to: str,
    subject: str,
    body_text: str,
    *,
    sender_name: str = "",
    html_body: str | None = None,
    attachment_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Send one email through the Gmail API. No browser or compose UI involved."""
    raw = _build_mime_message(sender, sender_name, to, subject, body_text, html_body, attachment_paths or [])
    raw_b64 = base64.urlsafe_b64encode(raw).decode("ascii")
    payload = json.dumps({"raw": raw_b64}).encode("utf-8")
    request = urllib.request.Request(
        GMAIL_SEND_URL,
        data=payload,
        method="POST",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gmail API send failed ({exc.code}): {detail}") from exc
