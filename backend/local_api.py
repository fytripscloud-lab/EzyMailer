from __future__ import annotations

import json
import hashlib
import hmac
import secrets
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pymysql
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn


API_HOST = "127.0.0.1"
# Fixed local API port used by the desktop app and docs UI.
API_PORT = 8765
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "ezymailer"

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
PASSWORD_ITERATIONS = 210000
PASSWORD_ALGORITHM = "sha256"

JWT_SECRET = "ezymailer-local-development-secret"
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 24 * 60

_server_thread: threading.Thread | None = None
_bootstrap_lock = threading.Lock()

app = FastAPI(
    title="EzyMailer Local API",
    version="1.0.0",
    description="Local development API for login, users, and app bootstrapping.",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)
    role: str = Field(default="user", min_length=1, max_length=32)


class ActivityLogRequest(BaseModel):
    category: str = Field(default="general", min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=128)
    details: dict[str, Any] = Field(default_factory=dict)


class BrowserSessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=128)
    browser_name: str = Field(default="Google Chrome", min_length=1, max_length=64)
    browser_mode: str = Field(default="Incognito", min_length=1, max_length=32)
    status: str = Field(default="Running", min_length=1, max_length=32)
    browser_pid: int | None = None
    launch_preset: str = Field(default="Default", max_length=64)
    details: dict[str, Any] = Field(default_factory=dict)


class SettingRequest(BaseModel):
    setting_key: str = Field(min_length=1, max_length=128)
    setting_value: Any


class ContentRequest(BaseModel):
    content_type: str = Field(default="message", min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    subject: str = Field(default="", max_length=255)
    body_text: str = Field(default="")
    body_html: str = Field(default="")
    details: dict[str, Any] = Field(default_factory=dict)


class ContentUpdateRequest(ContentRequest):
    content_id: int = Field(gt=0)


@app.get("/docs", include_in_schema=False)
def custom_docs() -> HTMLResponse:
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        oauth2_redirect_url="/docs/oauth2-redirect",
        init_oauth=None,
        swagger_ui_parameters={
            "docExpansion": "none",
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "filter": True,
            "syntaxHighlight.theme": "monokai",
        },
    )
    dark_css = """
    <style>
      :root {
        color-scheme: dark;
        --ez-bg: #0f1115;
        --ez-panel: #151a21;
        --ez-panel-2: #1b2230;
        --ez-border: #2c3442;
        --ez-text: #e5e7eb;
        --ez-muted: #9aa6b2;
        --ez-accent: #4ea1ff;
        --ez-success: #25c06d;
        --ez-danger: #f87171;
      }
      html, body {
        background: var(--ez-bg) !important;
        color: var(--ez-text) !important;
      }
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
      }
      .swagger-ui, .swagger-ui .wrapper {
        background: var(--ez-bg) !important;
        color: var(--ez-text) !important;
      }
      .swagger-ui .topbar {
        background: linear-gradient(180deg, #111725 0%, #0f1115 100%) !important;
        border-bottom: 1px solid var(--ez-border);
      }
      .swagger-ui .topbar a {
        color: var(--ez-text) !important;
      }
      .swagger-ui .info .title,
      .swagger-ui .info .title small,
      .swagger-ui .opblock-tag,
      .swagger-ui .opblock-summary-path,
      .swagger-ui .opblock-summary-description,
      .swagger-ui .parameter__name,
      .swagger-ui .parameter__type,
      .swagger-ui .parameter__in,
      .swagger-ui .response-col_status,
      .swagger-ui .response-col_links,
      .swagger-ui .response-col_description,
      .swagger-ui .model-title,
      .swagger-ui .model-box,
      .swagger-ui .tab li,
      .swagger-ui .tab button,
      .swagger-ui .btn,
      .swagger-ui .auth-wrapper .btn,
      .swagger-ui .modal-ux-header h3,
      .swagger-ui .scheme-container,
      .swagger-ui .parameter__extension,
      .swagger-ui .required,
      .swagger-ui .renderedMarkdown {
        color: var(--ez-text) !important;
      }
      .swagger-ui .scheme-container,
      .swagger-ui .opblock,
      .swagger-ui .opblock.opblock-get,
      .swagger-ui .opblock.opblock-post,
      .swagger-ui .opblock.opblock-put,
      .swagger-ui .opblock.opblock-delete,
      .swagger-ui .opblock.opblock-patch,
      .swagger-ui .opblock.opblock-options,
      .swagger-ui .opblock.opblock-head,
      .swagger-ui .opblock.opblock-trace,
      .swagger-ui .btn,
      .swagger-ui input[type=text],
      .swagger-ui input[type=password],
      .swagger-ui input[type=email],
      .swagger-ui textarea,
      .swagger-ui select,
      .swagger-ui .modal-ux {
        background: var(--ez-panel) !important;
        border-color: var(--ez-border) !important;
        color: var(--ez-text) !important;
      }
      .swagger-ui .opblock .opblock-summary,
      .swagger-ui .opblock .opblock-summary:hover {
        background: var(--ez-panel) !important;
      }
      .swagger-ui .opblock.opblock-get .opblock-summary-method { background: #276ef1 !important; }
      .swagger-ui .opblock.opblock-post .opblock-summary-method { background: #22c55e !important; }
      .swagger-ui .opblock.opblock-put .opblock-summary-method { background: #f59e0b !important; }
      .swagger-ui .opblock.opblock-delete .opblock-summary-method { background: #ef4444 !important; }
      .swagger-ui .opblock .opblock-summary-method {
        border: none !important;
        color: #fff !important;
        font-weight: 700 !important;
      }
      .swagger-ui .opblock .opblock-summary-path,
      .swagger-ui .opblock .opblock-summary-description {
        color: var(--ez-text) !important;
      }
      .swagger-ui table thead tr th,
      .swagger-ui table tbody tr td,
      .swagger-ui .responses-wrapper,
      .swagger-ui .responses-inner,
      .swagger-ui .response-col_status,
      .swagger-ui .response-col_description,
      .swagger-ui .response-col_media_type,
      .swagger-ui .parameters-col_description,
      .swagger-ui .parameter__name,
      .swagger-ui .parameter__default,
      .swagger-ui .parameter__in,
      .swagger-ui .parameter__type,
      .swagger-ui .col_header {
        background: transparent !important;
        color: var(--ez-text) !important;
        border-color: var(--ez-border) !important;
      }
      .swagger-ui .model,
      .swagger-ui .model-box {
        background: #10151d !important;
        border-color: var(--ez-border) !important;
      }
      .swagger-ui .model-box .property {
        color: var(--ez-text) !important;
      }
      .swagger-ui .btn.authorize {
        background: linear-gradient(180deg, #1f7de0 0%, #155fb4 100%) !important;
        border-color: #1f7de0 !important;
      }
      .swagger-ui .btn.execute {
        background: linear-gradient(180deg, #25c06d 0%, #159957 100%) !important;
        border-color: #25c06d !important;
      }
      .swagger-ui .btn:hover,
      .swagger-ui .btn:focus {
        filter: brightness(1.08);
      }
      .swagger-ui .dialog-ux,
      .swagger-ui .dialog-ux .backdrop-ux {
        background: rgba(0, 0, 0, 0.72) !important;
      }
      .swagger-ui section.models {
        border-color: var(--ez-border) !important;
      }
      .swagger-ui textarea,
      .swagger-ui input,
      .swagger-ui select {
        box-shadow: none !important;
      }
      .swagger-ui .opblock.opblock-get .opblock-summary {
        border-color: rgba(38, 99, 235, 0.6) !important;
      }
      .swagger-ui .opblock.opblock-post .opblock-summary {
        border-color: rgba(34, 197, 94, 0.6) !important;
      }
      .swagger-ui .opblock.opblock-put .opblock-summary {
        border-color: rgba(245, 158, 11, 0.6) !important;
      }
      .swagger-ui .opblock.opblock-delete .opblock-summary {
        border-color: rgba(239, 68, 68, 0.6) !important;
      }
      .swagger-ui .opblock-summary-control:focus,
      .swagger-ui .btn:focus,
      .swagger-ui input:focus,
      .swagger-ui select:focus,
      .swagger-ui textarea:focus {
        outline: 1px solid rgba(78, 161, 255, 0.45) !important;
        box-shadow: 0 0 0 3px rgba(78, 161, 255, 0.14) !important;
      }
      .swagger-ui .footer {
        background: transparent !important;
      }
    </style>
    """
    content = response.body.decode("utf-8").replace("</head>", f"{dark_css}</head>")
    return HTMLResponse(content=content, status_code=response.status_code)


@app.get("/docs/oauth2-redirect", include_in_schema=False)
def swagger_oauth2_redirect() -> HTMLResponse:
    return get_swagger_ui_oauth2_redirect_html()


def _connect(database: str | None = None):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        charset="utf8mb4",
        autocommit=True,
    )


def _ensure_schema() -> None:
    connection = _connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()

    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_db (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    username VARCHAR(64) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255) NULL,
                    password_salt VARCHAR(64) NULL,
                    role VARCHAR(32) NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            for column_sql in (
                "ALTER TABLE user_db ADD COLUMN password_hash VARCHAR(255) NULL",
                "ALTER TABLE user_db ADD COLUMN password_salt VARCHAR(64) NULL",
            ):
                try:
                    cursor.execute(column_sql)
                except pymysql.err.OperationalError as exc:
                    if exc.args and exc.args[0] == 1060:
                        pass
                    else:
                        raise
            cursor.execute(
                "SELECT id FROM user_db WHERE username = %s LIMIT 1",
                (DEFAULT_ADMIN_USERNAME,),
            )
            if cursor.fetchone() is None:
                salt, digest = _hash_password(DEFAULT_ADMIN_PASSWORD)
                cursor.execute(
                    """
                    INSERT INTO user_db (username, password, password_hash, password_salt, role)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (DEFAULT_ADMIN_USERNAME, "", digest, salt, "admin"),
                )
            else:
                _migrate_plaintext_passwords(cursor)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS login_history (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    success TINYINT(1) NOT NULL DEFAULT 0,
                    ip_address VARCHAR(45) NULL,
                    location_label VARCHAR(128) NULL,
                    user_agent VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_log (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    category VARCHAR(64) NOT NULL,
                    action VARCHAR(128) NOT NULL,
                    details_json LONGTEXT NULL,
                    ip_address VARCHAR(45) NULL,
                    location_label VARCHAR(128) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    session_id VARCHAR(128) NOT NULL UNIQUE,
                    title VARCHAR(128) NOT NULL,
                    browser_name VARCHAR(64) NOT NULL,
                    browser_mode VARCHAR(32) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    browser_pid BIGINT UNSIGNED NULL,
                    launch_preset VARCHAR(64) NULL,
                    details_json LONGTEXT NULL,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    setting_key VARCHAR(128) NOT NULL,
                    setting_value_json LONGTEXT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_user_setting (username, setting_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS content_library (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    content_type VARCHAR(64) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    subject VARCHAR(255) NOT NULL DEFAULT '',
                    body_text LONGTEXT NULL,
                    body_html LONGTEXT NULL,
                    details_json LONGTEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
    finally:
        connection.close()


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return salt, digest


def _verify_password(password: str, stored_hash: str | None, stored_salt: str | None, legacy_password: str | None) -> bool:
    if stored_hash and stored_salt:
        _, calculated = _hash_password(password, stored_salt)
        return hmac.compare_digest(calculated, stored_hash)
    return legacy_password is not None and hmac.compare_digest(password, legacy_password)


def _migrate_plaintext_passwords(cursor) -> None:
    cursor.execute(
        """
        SELECT id, password, password_hash, password_salt
        FROM user_db
        WHERE password_hash IS NULL OR password_salt IS NULL
        """
    )
    rows = cursor.fetchall() or []
    for row in rows:
        legacy_password = str(row[1] or "")
        if not legacy_password:
            continue
        salt, digest = _hash_password(legacy_password)
        cursor.execute(
            """
            UPDATE user_db
            SET password_hash = %s,
                password_salt = %s,
                password = ''
            WHERE id = %s
            """,
            (digest, salt, row[0]),
        )


def _create_token(user: dict[str, str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "uid": user["id"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _authenticate(username: str, password: str) -> dict[str, str] | None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, role, password, password_hash, password_salt
                FROM user_db
                WHERE username = %s
                """,
                (username,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if not _verify_password(password, row.get("password_hash"), row.get("password_salt"), row.get("password")):
                return None
            if not row.get("password_hash") or not row.get("password_salt") or row.get("password"):
                salt, digest = _hash_password(password)
                cursor.execute(
                    """
                    UPDATE user_db
                    SET password_hash = %s,
                        password_salt = %s,
                        password = ''
                    WHERE id = %s
                    """,
                    (digest, salt, row["id"]),
                )
            return {
                "id": str(row["id"]),
                "username": str(row["username"]),
                "role": str(row["role"]),
            }
    finally:
        connection.close()


def _create_user(username: str, password: str, role: str = "user") -> dict[str, str]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id FROM user_db WHERE username = %s LIMIT 1",
                (username,),
            )
            if cursor.fetchone() is not None:
                raise ValueError("User already exists.")

            salt, digest = _hash_password(password)
            cursor.execute(
                """
                INSERT INTO user_db (username, password, password_hash, password_salt, role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, "", digest, salt, role or "user"),
            )
            user_id = cursor.lastrowid
            return {
                "id": str(user_id),
                "username": username,
                "role": role or "user",
            }
    finally:
        connection.close()


def _list_users() -> list[dict[str, str]]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, role, created_at, updated_at
                FROM user_db
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall() or []
            return [
                {
                    "id": str(row["id"]),
                    "username": str(row["username"]),
                    "role": str(row["role"]),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                }
                for row in rows
            ]
    finally:
        connection.close()


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return None


def _location_label(ip_address: str | None) -> str | None:
    if ip_address in {"127.0.0.1", "::1", "localhost"}:
        return "Local machine"
    return None


def _persist_login_history(
    username: str,
    success: bool,
    request: Request | None = None,
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            ip_address = _client_ip(request)
            cursor.execute(
                """
                INSERT INTO login_history (user_id, username, success, ip_address, location_label, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    username,
                    1 if success else 0,
                    ip_address,
                    _location_label(ip_address),
                    request.headers.get("user-agent") if request is not None else None,
                ),
            )
    finally:
        connection.close()


def record_activity(
    username: str,
    action: str,
    category: str = "general",
    details: dict[str, Any] | None = None,
    request: Request | None = None,
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            ip_address = _client_ip(request)
            cursor.execute(
                """
                INSERT INTO activity_log (user_id, username, category, action, details_json, ip_address, location_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    username,
                    category,
                    action,
                    json.dumps(details or {}, ensure_ascii=False),
                    ip_address,
                    _location_label(ip_address),
                ),
            )
    finally:
        connection.close()


def upsert_setting(
    username: str,
    setting_key: str,
    setting_value: Any,
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_settings (user_id, username, setting_key, setting_value_json)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    user_id = VALUES(user_id),
                    setting_value_json = VALUES(setting_value_json)
                """,
                (user_id, username, setting_key, json.dumps(setting_value, ensure_ascii=False)),
            )
    finally:
        connection.close()


def record_browser_session(
    username: str,
    session_id: str,
    title: str,
    browser_name: str,
    browser_mode: str,
    status: str,
    browser_pid: int | None = None,
    launch_preset: str = "Default",
    details: dict[str, Any] | None = None,
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO browser_sessions (
                    user_id, username, session_id, title, browser_name, browser_mode,
                    status, browser_pid, launch_preset, details_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    user_id = VALUES(user_id),
                    title = VALUES(title),
                    browser_name = VALUES(browser_name),
                    browser_mode = VALUES(browser_mode),
                    status = VALUES(status),
                    browser_pid = VALUES(browser_pid),
                    launch_preset = VALUES(launch_preset),
                    details_json = VALUES(details_json),
                    updated_at = CURRENT_TIMESTAMP,
                    closed_at = IF(VALUES(status) IN ('Closed', 'Stopped'), CURRENT_TIMESTAMP, closed_at)
                """,
                (
                    user_id,
                    username,
                    session_id,
                    title,
                    browser_name,
                    browser_mode,
                    status,
                    browser_pid,
                    launch_preset,
                    json.dumps(details or {}, ensure_ascii=False),
                ),
            )
    finally:
        connection.close()


def record_content(
    username: str,
    content_type: str,
    title: str,
    subject: str = "",
    body_text: str = "",
    body_html: str = "",
    details: dict[str, Any] | None = None,
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO content_library (
                    user_id, username, content_type, title, subject, body_text, body_html, details_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    username,
                    content_type,
                    title,
                    subject,
                    body_text,
                    body_html,
                    json.dumps(details or {}, ensure_ascii=False),
                ),
            )
    finally:
        connection.close()


def _decode_bearer_token(authorization: str | None) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    return {
        "id": str(payload.get("uid", "")),
        "username": str(payload.get("sub", "")),
        "role": str(payload.get("role", "")),
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    user = _decode_bearer_token(authorization)
    if not user["username"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    return user


@app.on_event("startup")
def _startup() -> None:
    _ensure_schema()


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "ezymailer-local-api", "database": DB_NAME}


@app.post("/api/login")
def login(payload: LoginRequest, request: Request) -> dict[str, object]:
    user = _authenticate(payload.username.strip(), payload.password)
    if user is None:
        _persist_login_history(payload.username.strip(), False, request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    _persist_login_history(payload.username.strip(), True, request=request, user_id=int(user["id"]))
    token = _create_token(user)
    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.get("/api/users")
def users(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return {"ok": True, "users": _list_users()}


@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    try:
        user = _create_user(payload.username.strip(), payload.password, payload.role.strip() or "user")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.post("/api/activity")
def create_activity(
    payload: ActivityLogRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    record_activity(
        current_user["username"],
        payload.action,
        payload.category,
        payload.details,
        user_id=int(current_user["id"]) if current_user.get("id") else None,
    )
    return {"ok": True}


@app.get("/api/activity")
def list_activity(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, category, action, details_json, created_at
                FROM activity_log
                WHERE username = %s
                ORDER BY id DESC
                LIMIT 200
                """,
                (current_user["username"],),
            )
            rows = cursor.fetchall() or []
            return {"ok": True, "activity": rows}
    finally:
        connection.close()


@app.post("/api/browser-sessions")
def create_browser_session(
    payload: BrowserSessionRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    record_browser_session(
        current_user["username"],
        payload.session_id,
        payload.title,
        payload.browser_name,
        payload.browser_mode,
        payload.status,
        payload.browser_pid,
        payload.launch_preset,
        payload.details,
        user_id=int(current_user["id"]) if current_user.get("id") else None,
    )
    return {"ok": True}


@app.get("/api/browser-sessions")
def list_browser_sessions(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT session_id, title, browser_name, browser_mode, status, browser_pid,
                       launch_preset, details_json, started_at, updated_at, closed_at
                FROM browser_sessions
                WHERE username = %s
                ORDER BY id DESC
                """,
                (current_user["username"],),
            )
            rows = cursor.fetchall() or []
            return {"ok": True, "sessions": rows}
    finally:
        connection.close()


@app.post("/api/settings")
def upsert_setting_endpoint(
    payload: SettingRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    upsert_setting(
        current_user["username"],
        payload.setting_key,
        payload.setting_value,
        user_id=int(current_user["id"]) if current_user.get("id") else None,
    )
    return {"ok": True}


@app.get("/api/settings")
def list_settings(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT setting_key, setting_value_json, updated_at
                FROM user_settings
                WHERE username = %s
                ORDER BY setting_key ASC
                """,
                (current_user["username"],),
            )
            rows = cursor.fetchall() or []
            return {"ok": True, "settings": rows}
    finally:
        connection.close()


@app.post("/api/content")
def create_content(
    payload: ContentRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    record_content(
        current_user["username"],
        payload.content_type,
        payload.title,
        payload.subject,
        payload.body_text,
        payload.body_html,
        payload.details,
        user_id=int(current_user["id"]) if current_user.get("id") else None,
    )
    return {"ok": True}


@app.get("/api/content")
def list_content(
    content_type: str | None = None,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            params: list[Any] = [current_user["username"]]
            type_clause = ""
            if content_type:
                type_clause = " AND content_type = %s"
                params.append(content_type)
            cursor.execute(
                """
                SELECT id, content_type, title, subject, body_text, body_html, details_json, created_at, updated_at
                FROM content_library
                WHERE username = %s
                """ + type_clause + """
                ORDER BY id DESC
                """,
                tuple(params),
            )
            rows = cursor.fetchall() or []
            return {"ok": True, "content": rows}
    finally:
        connection.close()


@app.put("/api/content/{content_id}")
def update_content(
    content_id: int,
    payload: ContentRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE content_library
                SET content_type = %s,
                    title = %s,
                    subject = %s,
                    body_text = %s,
                    body_html = %s,
                    details_json = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND username = %s
                """,
                (
                    payload.content_type,
                    payload.title,
                    payload.subject,
                    payload.body_text,
                    payload.body_html,
                    json.dumps(payload.details or {}, ensure_ascii=False),
                    content_id,
                    current_user["username"],
                ),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    finally:
        connection.close()
    return {"ok": True}


@app.delete("/api/content/{content_id}")
def delete_content(
    content_id: int,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM content_library WHERE id = %s AND username = %s",
                (content_id, current_user["username"]),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found.")
    finally:
        connection.close()
    return {"ok": True}


def ensure_api_server() -> None:
    global _server_thread

    with _bootstrap_lock:
        if _server_thread is not None and _server_thread.is_alive():
            return

        try:
            with urllib.request.urlopen(f"{API_BASE_URL}/api/health", timeout=0.5):
                return
        except Exception:
            pass

        _ensure_schema()
        config = uvicorn.Config(
            app,
            host=API_HOST,
            port=API_PORT,
            log_level="warning",
            access_log=False,
            reload=False,
        )
        server = uvicorn.Server(config)
        _server_thread = threading.Thread(target=server.run, name="EzyMailerLocalAPI", daemon=True)
        _server_thread.start()

        for _ in range(50):
            try:
                with urllib.request.urlopen(f"{API_BASE_URL}/api/health", timeout=0.5):
                    return
            except Exception:
                threading.Event().wait(0.1)


def login(username: str, password: str, timeout: float = 5.0) -> dict:
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE_URL}/api/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _authorized_request(
    method: str,
    path: str,
    auth_token: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 5.0,
    query: dict[str, Any] | None = None,
) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {auth_token}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    url = f"{API_BASE_URL}{path}"
    if query:
        from urllib.parse import urlencode

        url = f"{url}?{urlencode(query)}"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_settings(auth_token: str, timeout: float = 5.0) -> dict:
    return _authorized_request("GET", "/api/settings", auth_token, timeout=timeout)


def get_content(auth_token: str, timeout: float = 5.0, content_type: str | None = None) -> dict:
    query = {"content_type": content_type} if content_type else None
    return _authorized_request("GET", "/api/content", auth_token, timeout=timeout, query=query)


def save_content(
    auth_token: str,
    content_type: str,
    title: str,
    subject: str = "",
    body_text: str = "",
    body_html: str = "",
    details: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict:
    return _authorized_request(
        "POST",
        "/api/content",
        auth_token,
        {
            "content_type": content_type,
            "title": title,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "details": details or {},
        },
        timeout=timeout,
    )


def update_content(
    auth_token: str,
    content_id: int,
    content_type: str,
    title: str,
    subject: str = "",
    body_text: str = "",
    body_html: str = "",
    details: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict:
    return _authorized_request(
        "PUT",
        f"/api/content/{content_id}",
        auth_token,
        {
            "content_id": content_id,
            "content_type": content_type,
            "title": title,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "details": details or {},
        },
        timeout=timeout,
    )


def delete_content(auth_token: str, content_id: int, timeout: float = 5.0) -> dict:
    return _authorized_request("DELETE", f"/api/content/{content_id}", auth_token, timeout=timeout)
