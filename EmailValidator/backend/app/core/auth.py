import os
import time

import httpx
import jwt
from fastapi import Header, HTTPException, Query, status

# Fast path only: matches whenever ezymailer's own backend/local_api.py
# happens to be using its own dev-default secret too (e.g. a local dev
# backend). A real production login signs its token with the live server's
# own secret instead - one this desktop-bundled process has no business
# holding (shipping a server secret inside distributable software would
# defeat the point of it being secret) - so those tokens fall through to
# the real check below.
JWT_SECRET = os.getenv("EZYM_MAILER_JWT_SECRET", "ezymailer-local-development-secret")
JWT_ALGORITHM = "HS256"

_TOKEN_CACHE_TTL_SECONDS = 60
_verified_tokens: dict[str, float] = {}


def _ezymailer_api_base_url() -> str:
    # Read fresh each call (not cached at import time) so tests can
    # monkeypatch it after this module is already imported.
    return os.getenv("EZYM_MAILER_API_BASE_URL", "http://15.206.161.73:8765")


def _cached_and_fresh(raw_token: str) -> bool:
    expiry = _verified_tokens.get(raw_token)
    if expiry is None:
        return False
    if expiry < time.time():
        del _verified_tokens[raw_token]
        return False
    return True


async def _verify_with_ezymailer_backend(raw_token: str) -> bool:
    """The real check for a production token: ask the same backend that
    issued it (ezymailer's own /api/login) whether it's still valid, via any
    endpoint gated behind its get_current_user dependency."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            response = await http_client.get(
                f"{_ezymailer_api_base_url()}/api/settings",
                headers={"Authorization": f"Bearer {raw_token}"},
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def _unverified_claims(raw_token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(raw_token, options={"verify_signature": False, "verify_exp": False})
    except jwt.InvalidTokenError:
        payload = {}
    return {"username": str(payload.get("sub", "")), "role": str(payload.get("role", ""))}


async def verify_token(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> dict[str, str]:
    """Accepts the token either as a Bearer header (axios calls) or a
    ?token= query param (plain <a href> export downloads, which can't set
    headers)."""
    raw = None
    if authorization and authorization.startswith("Bearer "):
        raw = authorization.removeprefix("Bearer ").strip()
    elif token:
        raw = token

    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"username": str(payload.get("sub", "")), "role": str(payload.get("role", ""))}
    except jwt.InvalidTokenError:
        pass

    if _cached_and_fresh(raw):
        return _unverified_claims(raw)

    if await _verify_with_ezymailer_backend(raw):
        _verified_tokens[raw] = time.time() + _TOKEN_CACHE_TTL_SECONDS
        return _unverified_claims(raw)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
