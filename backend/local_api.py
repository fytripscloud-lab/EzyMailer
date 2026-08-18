from __future__ import annotations

import json
import hashlib
import hmac
import os
from pathlib import Path
import re
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


API_HOST = os.getenv("EZYM_MAILER_API_HOST", "127.0.0.1")
# Fixed local API port used by the desktop app and docs UI.
API_PORT = int(os.getenv("EZYM_MAILER_API_PORT", "8765"))
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

_DB_CREDENTIALS_PATH = Path(__file__).resolve().parents[1] / "server_credentials" / "Database_Credentials"


def _normalize_db_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _load_db_credentials() -> dict[str, str]:
    credentials: dict[str, str] = {}
    if not _DB_CREDENTIALS_PATH.exists():
        return credentials
    for raw_line in _DB_CREDENTIALS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        separator = ":" if ":" in line else "=" if "=" in line else None
        if separator is None:
            continue
        key, value = line.split(separator, 1)
        credentials[_normalize_db_key(key)] = value.strip()
    return credentials


_LIVE_DB_CREDENTIALS = _load_db_credentials()


def _db_config_value(env_name: str, fallback_keys: tuple[str, ...], default: str = "") -> str:
    env_value = os.getenv(env_name)
    if env_value not in {None, ""}:
        return env_value
    for key in fallback_keys:
        fallback_value = _LIVE_DB_CREDENTIALS.get(key)
        if fallback_value not in {None, ""}:
            return fallback_value
    return default


DB_HOST = _db_config_value("EZYM_MAILER_DB_HOST", ("endpoint", "host"))
DB_PORT = int(_db_config_value("EZYM_MAILER_DB_PORT", ("port",), "3306"))
DB_USER = _db_config_value("EZYM_MAILER_DB_USER", ("user_name", "username", "user"))
DB_PASSWORD = _db_config_value("EZYM_MAILER_DB_PASSWORD", ("password",))
DB_NAME = os.getenv("EZYM_MAILER_DB_NAME", "ezymailer")

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
PASSWORD_ITERATIONS = 210000
PASSWORD_ALGORITHM = "sha256"

JWT_SECRET = os.getenv("EZYM_MAILER_JWT_SECRET", "ezymailer-local-development-secret")
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
    device_fingerprint: str | None = Field(default=None, max_length=255)
    device_name: str | None = Field(default=None, max_length=255)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)
    role: str = Field(default="user", min_length=1, max_length=32)
    display_name: str = Field(default="", max_length=128)
    is_active: bool = True
    login_valid_until: datetime | None = None


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    login_valid_until: datetime | None = None
    reset_password: str | None = Field(default=None, max_length=255)
    clear_device_binding: bool = False


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=255)


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


class TagStateRequest(BaseModel):
    state_key: str = Field(default="tag_state", min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


class CustomerVariableRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    variables: dict[str, Any] = Field(default_factory=dict)


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
    if not DB_HOST or not DB_USER or not DB_PASSWORD:
        raise RuntimeError("Live database credentials are not configured.")
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
                    display_name VARCHAR(128) NOT NULL DEFAULT '',
                    role VARCHAR(32) NOT NULL DEFAULT 'user',
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    login_valid_until TIMESTAMP NULL DEFAULT NULL,
                    session_version BIGINT UNSIGNED NOT NULL DEFAULT 0,
                    device_fingerprint VARCHAR(255) NULL,
                    device_name VARCHAR(255) NULL,
                    device_ip VARCHAR(45) NULL,
                    device_bound_at TIMESTAMP NULL DEFAULT NULL,
                    last_login_at TIMESTAMP NULL DEFAULT NULL,
                    last_login_ip VARCHAR(45) NULL,
                    last_login_device VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            for column_sql in (
                "ALTER TABLE user_db ADD COLUMN password_hash VARCHAR(255) NULL",
                "ALTER TABLE user_db ADD COLUMN password_salt VARCHAR(64) NULL",
                "ALTER TABLE user_db ADD COLUMN display_name VARCHAR(128) NOT NULL DEFAULT ''",
                "ALTER TABLE user_db ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1",
                "ALTER TABLE user_db ADD COLUMN login_valid_until TIMESTAMP NULL DEFAULT NULL",
                "ALTER TABLE user_db ADD COLUMN session_version BIGINT UNSIGNED NOT NULL DEFAULT 0",
                "ALTER TABLE user_db ADD COLUMN device_fingerprint VARCHAR(255) NULL",
                "ALTER TABLE user_db ADD COLUMN device_name VARCHAR(255) NULL",
                "ALTER TABLE user_db ADD COLUMN device_ip VARCHAR(45) NULL",
                "ALTER TABLE user_db ADD COLUMN device_bound_at TIMESTAMP NULL DEFAULT NULL",
                "ALTER TABLE user_db ADD COLUMN last_login_at TIMESTAMP NULL DEFAULT NULL",
                "ALTER TABLE user_db ADD COLUMN last_login_ip VARCHAR(45) NULL",
                "ALTER TABLE user_db ADD COLUMN last_login_device VARCHAR(255) NULL",
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
                    device_fingerprint VARCHAR(255) NULL,
                    device_name VARCHAR(255) NULL,
                    location_label VARCHAR(128) NULL,
                    user_agent VARCHAR(255) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            for column_sql in (
                "ALTER TABLE login_history ADD COLUMN device_fingerprint VARCHAR(255) NULL",
                "ALTER TABLE login_history ADD COLUMN device_name VARCHAR(255) NULL",
            ):
                try:
                    cursor.execute(column_sql)
                except pymysql.err.OperationalError as exc:
                    if exc.args and exc.args[0] == 1060:
                        pass
                    else:
                        raise
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tag_state (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    state_key VARCHAR(128) NOT NULL DEFAULT 'tag_state',
                    payload_json LONGTEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_user_tag_state (username, state_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_variables (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT UNSIGNED NULL,
                    username VARCHAR(64) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    variables_json LONGTEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_user_customer_variables (username, email)
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


def _create_token(user: dict[str, str], session_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "uid": user["id"],
        "ver": int(session_version or 0),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _authenticate(
    username: str,
    password: str,
    request: Request | None = None,
    device_fingerprint: str | None = None,
    device_name: str | None = None,
    bypass_device_restriction: bool = False,
) -> dict[str, str] | None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, role, is_active, login_valid_until,
                       device_fingerprint, device_name, device_ip,
                       password, password_hash, password_salt
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
            _assert_user_login_allowed(row, request, device_fingerprint, bypass_device_restriction=bypass_device_restriction)
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
            if not str(row.get("device_fingerprint") or "").strip():
                session_version = _bind_or_refresh_device(int(row["id"]), device_fingerprint, device_name, request)
            else:
                session_version = _bind_or_refresh_device(int(row["id"]), row.get("device_fingerprint"), row.get("device_name"), request)
            return {
                "id": str(row["id"]),
                "username": str(row["username"]),
                "display_name": str(row.get("display_name") or ""),
                "role": str(row["role"]),
                "session_version": str(session_version),
            }
    finally:
        connection.close()


def _create_user(
    username: str,
    password: str,
    role: str = "user",
    display_name: str = "",
    is_active: bool = True,
    login_valid_until: datetime | None = None,
) -> dict[str, Any]:
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
                INSERT INTO user_db (username, password, password_hash, password_salt, display_name, role, is_active, login_valid_until)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    username,
                    "",
                    digest,
                    salt,
                    display_name or "",
                    role or "user",
                    1 if is_active else 0,
                    login_valid_until,
                ),
            )
            user_id = cursor.lastrowid
            return {
                "id": str(user_id),
                "username": username,
                "display_name": display_name or "",
                "role": role or "user",
                "is_active": bool(is_active),
                "login_valid_until": login_valid_until,
            }
    finally:
        connection.close()


def _list_users() -> list[dict[str, str]]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, role, is_active, login_valid_until,
                       device_fingerprint, device_name, device_ip, device_bound_at,
                       last_login_at, last_login_ip, last_login_device, created_at, updated_at
                FROM user_db
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall() or []
            return [_user_row_to_dict(row) for row in rows]
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
    device_fingerprint: str | None = None,
    device_name: str | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            ip_address = _client_ip(request)
            cursor.execute(
                """
                INSERT INTO login_history (
                    user_id, username, success, ip_address, device_fingerprint,
                    device_name, location_label, user_agent
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    username,
                    1 if success else 0,
                    ip_address,
                    (device_fingerprint or "").strip() or None,
                    (device_name or "").strip() or None,
                    _location_label(ip_address),
                    request.headers.get("user-agent") if request is not None else None,
                ),
            )
    finally:
        connection.close()


def _parse_login_valid_until(value: object) -> datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _user_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "username": str(row["username"]),
        "display_name": str(row.get("display_name") or ""),
        "role": str(row["role"]),
        "is_active": bool(row.get("is_active", 1)),
        "login_valid_until": row.get("login_valid_until"),
        "session_version": str(row.get("session_version") or 0),
        "device_fingerprint": str(row.get("device_fingerprint") or ""),
        "device_name": str(row.get("device_name") or ""),
        "device_ip": str(row.get("device_ip") or ""),
        "last_login_at": row.get("last_login_at"),
        "last_login_ip": str(row.get("last_login_ip") or ""),
        "last_login_device": str(row.get("last_login_device") or ""),
        "device_bound_at": row.get("device_bound_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _build_device_history(login_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in reversed(login_rows):
        if not row.get("success"):
            continue
        fingerprint = str(row.get("device_fingerprint") or "").strip()
        device_name = str(row.get("device_name") or "").strip()
        ip_address = str(row.get("ip_address") or "").strip()
        key = fingerprint or device_name or ip_address or f"row-{row.get('id')}"
        created_at = row.get("created_at")
        bucket = grouped.setdefault(
            key,
            {
                "key": key,
                "device_fingerprint": fingerprint,
                "device_name": device_name,
                "ip_address": ip_address,
                "first_seen_at": created_at,
                "last_seen_at": created_at,
                "login_count": 0,
                "success_count": 0,
                "last_user_agent": str(row.get("user_agent") or ""),
                "location_label": str(row.get("location_label") or ""),
            },
        )
        bucket["login_count"] += 1
        bucket["success_count"] += 1
        if created_at and (bucket["first_seen_at"] is None or created_at < bucket["first_seen_at"]):
            bucket["first_seen_at"] = created_at
        if created_at and (bucket["last_seen_at"] is None or created_at > bucket["last_seen_at"]):
            bucket["last_seen_at"] = created_at
            bucket["last_user_agent"] = str(row.get("user_agent") or "")
            bucket["location_label"] = str(row.get("location_label") or "")
            bucket["ip_address"] = ip_address
            bucket["device_name"] = device_name
            bucket["device_fingerprint"] = fingerprint
    return sorted(grouped.values(), key=lambda item: item["last_seen_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


def _is_user_online(user_row: dict[str, Any]) -> bool:
    if not bool(user_row.get("is_active", 1)):
        return False
    valid_until = _parse_login_valid_until(user_row.get("login_valid_until"))
    if valid_until is not None:
        now = datetime.now(timezone.utc)
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        if valid_until < now:
            return False
    last_login_at = user_row.get("last_login_at")
    if not isinstance(last_login_at, datetime):
        return False
    if last_login_at.tzinfo is None:
        last_login_at = last_login_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_login_at) <= timedelta(minutes=15)


def _get_user_by_username(username: str) -> dict[str, Any] | None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, role, is_active, login_valid_until, session_version,
                       device_fingerprint, device_name, device_ip, device_bound_at,
                       last_login_at, last_login_ip, last_login_device, created_at, updated_at,
                       password, password_hash, password_salt
                FROM user_db
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )
            row = cursor.fetchone()
            return row if row else None
    finally:
        connection.close()


def _device_key_from_request(request: Request | None, device_fingerprint: str | None) -> str:
    fingerprint = (device_fingerprint or "").strip()
    ip_address = _client_ip(request) or ""
    parts = [fingerprint, ip_address]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _assert_user_login_allowed(
    row: dict[str, Any],
    request: Request | None,
    device_fingerprint: str | None,
    bypass_device_restriction: bool = False,
) -> None:
    if not bool(row.get("is_active", 1)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")
    valid_until = _parse_login_valid_until(row.get("login_valid_until"))
    if valid_until is not None:
        now = datetime.now(timezone.utc)
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        if valid_until < now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User login has expired.")

    # Latest successful login always becomes the active session.
    # Device history is tracked for audit and display, but it does not block login.


def _bind_or_refresh_device(
    user_id: int,
    device_fingerprint: str | None,
    device_name: str | None,
    request: Request | None,
) -> int:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            ip_address = _client_ip(request)
            cursor.execute(
                """
                UPDATE user_db
                SET device_fingerprint = COALESCE(NULLIF(%s, ''), device_fingerprint),
                    device_name = COALESCE(NULLIF(%s, ''), device_name),
                    device_ip = COALESCE(NULLIF(%s, ''), device_ip),
                    session_version = COALESCE(session_version, 0) + 1,
                    device_bound_at = CASE
                        WHEN device_fingerprint IS NULL OR device_fingerprint = '' THEN CURRENT_TIMESTAMP
                        ELSE device_bound_at
                    END,
                    last_login_at = CURRENT_TIMESTAMP,
                    last_login_ip = %s,
                    last_login_device = %s
                WHERE id = %s
                """,
                (
                    (device_fingerprint or "").strip(),
                    (device_name or "").strip(),
                    (ip_address or "").strip(),
                    ip_address,
                    device_name or "",
                    user_id,
                ),
            )
            cursor.execute(
                "SELECT session_version FROM user_db WHERE id = %s LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
            return int((row or {}).get("session_version") or 0)
    finally:
        connection.close()


def _rename_user_everywhere(old_username: str, new_username: str) -> None:
    old_username = old_username.strip()
    new_username = new_username.strip()
    if not old_username or not new_username or old_username == new_username:
        return
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            for table, column in (
                ("login_history", "username"),
                ("activity_log", "username"),
                ("browser_sessions", "username"),
                ("user_settings", "username"),
                ("content_library", "username"),
                ("tag_state", "username"),
                ("customer_variables", "username"),
            ):
                cursor.execute(
                    f"UPDATE {table} SET {column} = %s WHERE {column} = %s",
                    (new_username, old_username),
                )
            cursor.execute(
                "UPDATE user_db SET username = %s WHERE username = %s",
                (new_username, old_username),
            )
    finally:
        connection.close()


def _update_user_record(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id, username, display_name, role, is_active, login_valid_until, device_fingerprint, device_name, device_ip, device_bound_at, last_login_at, last_login_ip, last_login_device, created_at, updated_at FROM user_db WHERE id = %s LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("User not found.")

            old_username = str(row["username"])
            new_username = str(payload.get("username") or old_username).strip() or old_username
            display_name = str(payload.get("display_name") or row.get("display_name") or "").strip()
            role = str(payload.get("role") or row.get("role") or "user").strip() or "user"
            is_active = payload.get("is_active")
            login_valid_until = payload.get("login_valid_until")
            reset_password = str(payload.get("reset_password") or "").strip()
            clear_device_binding = bool(payload.get("clear_device_binding"))

            if new_username != old_username:
                cursor.execute(
                    "SELECT id FROM user_db WHERE username = %s AND id <> %s LIMIT 1",
                    (new_username, user_id),
                )
                if cursor.fetchone() is not None:
                    raise ValueError("Username already exists.")
                cursor.execute(
                    "UPDATE user_db SET username = %s WHERE id = %s",
                    (new_username, user_id),
                )
                _rename_user_everywhere(old_username, new_username)
                row["username"] = new_username

            update_parts = ["display_name = %s", "role = %s"]
            params: list[Any] = [display_name, role]
            if is_active is not None:
                update_parts.append("is_active = %s")
                params.append(1 if bool(is_active) else 0)
            if login_valid_until is not None:
                update_parts.append("login_valid_until = %s")
                params.append(login_valid_until)
            if reset_password:
                salt, digest = _hash_password(reset_password)
                update_parts.extend(["password = %s", "password_hash = %s", "password_salt = %s"])
                params.extend(["", digest, salt])
            if clear_device_binding:
                update_parts.extend(
                    [
                        "device_fingerprint = NULL",
                        "device_name = NULL",
                        "device_ip = NULL",
                        "device_bound_at = NULL",
                    ]
                )

            params.append(user_id)
            cursor.execute(
                f"UPDATE user_db SET {', '.join(update_parts)} WHERE id = %s",
                params,
            )
            cursor.execute(
                "SELECT id, username, display_name, role, is_active, login_valid_until, device_fingerprint, device_name, device_ip, device_bound_at, last_login_at, last_login_ip, last_login_device, created_at, updated_at FROM user_db WHERE id = %s LIMIT 1",
                (user_id,),
            )
            updated = cursor.fetchone()
            if updated is None:
                raise ValueError("User not found.")
            return _user_row_to_dict(updated)
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


def upsert_tag_state(
    username: str,
    payload: dict[str, Any],
    state_key: str = "tag_state",
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tag_state (user_id, username, state_key, payload_json)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    user_id = VALUES(user_id),
                    payload_json = VALUES(payload_json),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, username, state_key, json.dumps(payload, ensure_ascii=False)),
            )
    finally:
        connection.close()


def delete_tag_state(
    username: str,
    state_key: str = "tag_state",
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tag_state WHERE username = %s AND state_key = %s",
                (username, state_key),
            )
    finally:
        connection.close()


def upsert_customer_variables(
    username: str,
    email: str,
    variables: dict[str, Any],
    user_id: int | None = None,
) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO customer_variables (user_id, username, email, variables_json)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    user_id = VALUES(user_id),
                    variables_json = VALUES(variables_json),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, username, email.strip().lower(), json.dumps(variables, ensure_ascii=False)),
            )
    finally:
        connection.close()


def delete_customer_variables(username: str, email: str | None = None) -> None:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor() as cursor:
            if email:
                cursor.execute(
                    "DELETE FROM customer_variables WHERE username = %s AND email = %s",
                    (username, email.strip().lower()),
                )
            else:
                cursor.execute(
                    "DELETE FROM customer_variables WHERE username = %s",
                    (username,),
                )
    finally:
        connection.close()


def _decode_bearer_token(authorization: str | None) -> dict[str, Any]:
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
        "session_version": int(payload.get("ver", 0) or 0),
    }


def _require_admin(current_user: dict[str, str]) -> None:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    user = _decode_bearer_token(authorization)
    if not user["username"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    row = _get_user_by_username(user["username"])
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if not bool(row.get("is_active", 1)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")
    valid_until = _parse_login_valid_until(row.get("login_valid_until"))
    if valid_until is not None:
        now = datetime.now(timezone.utc)
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        if valid_until < now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User login has expired.")
    if int(user.get("session_version", 0)) != int(row.get("session_version") or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired due to a newer login.")
    user["display_name"] = str(row.get("display_name") or "")
    user["is_active"] = "1" if bool(row.get("is_active", 1)) else "0"
    return user


@app.on_event("startup")
def _startup() -> None:
    _ensure_schema()


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "ezymailer-local-api", "database": DB_NAME}


@app.post("/api/login")
def login(payload: LoginRequest, request: Request) -> dict[str, object]:
    user = _authenticate(
        payload.username.strip(),
        payload.password,
        request=request,
        device_fingerprint=payload.device_fingerprint,
        device_name=payload.device_name,
    )
    if user is None:
        _persist_login_history(
            payload.username.strip(),
            False,
            request=request,
            device_fingerprint=payload.device_fingerprint,
            device_name=payload.device_name,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    _persist_login_history(
        payload.username.strip(),
        True,
        request=request,
        user_id=int(user["id"]),
        device_fingerprint=payload.device_fingerprint,
        device_name=payload.device_name,
    )
    token = _create_token(user, int(user.get("session_version", 0) or 0))
    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.post("/api/admin/login")
def admin_login(payload: LoginRequest, request: Request) -> dict[str, object]:
    user = _authenticate(
        payload.username.strip(),
        payload.password,
        request=request,
        device_fingerprint=payload.device_fingerprint,
        device_name=payload.device_name,
        bypass_device_restriction=True,
    )
    if user is None:
        _persist_login_history(
            payload.username.strip(),
            False,
            request=request,
            device_fingerprint=payload.device_fingerprint,
            device_name=payload.device_name,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if str(user.get("role") or "").lower() != "admin":
        _persist_login_history(
            payload.username.strip(),
            False,
            request=request,
            user_id=int(user["id"]),
            device_fingerprint=payload.device_fingerprint,
            device_name=payload.device_name,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    _persist_login_history(
        payload.username.strip(),
        True,
        request=request,
        user_id=int(user["id"]),
        device_fingerprint=payload.device_fingerprint,
        device_name=payload.device_name,
    )
    token = _create_token(user, int(user.get("session_version", 0) or 0))
    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@app.get("/api/users")
def users(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    _require_admin(current_user)
    return {"ok": True, "users": _list_users()}


@app.get("/api/admin/users")
def admin_list_users(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    _require_admin(current_user)
    return {"ok": True, "users": _list_users()}


@app.get("/api/admin/users/{user_id}/details")
def admin_get_user_details(
    user_id: int,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, role, is_active, login_valid_until,
                       device_fingerprint, device_name, device_ip, device_bound_at,
                       last_login_at, last_login_ip, last_login_device, created_at, updated_at
                FROM user_db
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            user_row = cursor.fetchone()
            if user_row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            user = _user_row_to_dict(user_row)
            online = _is_user_online(user_row)

            cursor.execute(
                """
                SELECT id, user_id, username, success, ip_address, device_fingerprint, device_name,
                       location_label, user_agent, created_at
                FROM login_history
                WHERE user_id = %s OR username = %s
                ORDER BY id DESC
                LIMIT 200
                """,
                (user_id, str(user_row["username"])),
            )
            login_rows = cursor.fetchall() or []

            cursor.execute(
                """
                SELECT id, username, category, action, details_json, ip_address, location_label, created_at
                FROM activity_log
                WHERE user_id = %s OR username = %s
                ORDER BY id DESC
                LIMIT 100
                """,
                (user_id, str(user_row["username"])),
            )
            activity_rows = cursor.fetchall() or []

            return {
                "ok": True,
                "user": user,
                "online_status": online,
                "online_status_label": "Online" if online else "Offline",
                "login_history": login_rows,
                "activity": activity_rows,
                "device_history": _build_device_history(login_rows),
                "current_device": {
                    "device_fingerprint": str(user_row.get("device_fingerprint") or ""),
                    "mac_id": str(user_row.get("device_fingerprint") or ""),
                    "device_name": str(user_row.get("device_name") or ""),
                    "device_ip": str(user_row.get("device_ip") or ""),
                    "last_login_device": str(user_row.get("last_login_device") or ""),
                    "device_bound_at": user_row.get("device_bound_at"),
                },
            }
    finally:
        connection.close()


@app.get("/api/admin/users/{user_id}")
def admin_get_user(
    user_id: int,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, role, is_active, login_valid_until,
                       device_fingerprint, device_name, device_ip, device_bound_at,
                       last_login_at, last_login_ip, last_login_device, created_at, updated_at
                FROM user_db
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            return {"ok": True, "user": _user_row_to_dict(row)}
    finally:
        connection.close()


@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    try:
        user = _create_user(
            payload.username.strip(),
            payload.password,
            payload.role.strip() or "user",
            payload.display_name.strip(),
            payload.is_active,
            payload.login_valid_until,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    payload: UpdateUserRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    try:
        user = _update_user_record(user_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    try:
        user = _update_user_record(user_id, {"reset_password": payload.password})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.post("/api/admin/users/{user_id}/activate")
def admin_activate_user(
    user_id: int,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    try:
        user = _update_user_record(user_id, {"is_active": True})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.post("/api/admin/users/{user_id}/deactivate")
def admin_deactivate_user(
    user_id: int,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    try:
        user = _update_user_record(user_id, {"is_active": False})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.post("/api/admin/users/{user_id}/reset-device")
def admin_reset_device_binding(
    user_id: int,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    try:
        user = _update_user_record(user_id, {"clear_device_binding": True})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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


@app.get("/api/admin/activity")
def admin_list_activity(
    username: str | None = None,
    limit: int = 200,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    limit = max(1, min(int(limit or 200), 500))
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            params: list[Any] = []
            where_clause = ""
            if username:
                where_clause = "WHERE username = %s"
                params.append(username.strip())
            cursor.execute(
                f"""
                SELECT id, username, category, action, details_json, ip_address, location_label, created_at
                FROM activity_log
                {where_clause}
                ORDER BY id DESC
                LIMIT %s
                """,
                (*params, limit),
            )
            rows = cursor.fetchall() or []
            return {"ok": True, "activity": rows}
    finally:
        connection.close()


@app.get("/api/admin/login-history")
def admin_list_login_history(
    username: str | None = None,
    limit: int = 200,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    _require_admin(current_user)
    limit = max(1, min(int(limit or 200), 500))
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            params: list[Any] = []
            where_clause = ""
            if username:
                where_clause = "WHERE username = %s"
                params.append(username.strip())
            cursor.execute(
                f"""
                SELECT id, user_id, username, success, ip_address, device_fingerprint, device_name,
                       location_label, user_agent, created_at
                FROM login_history
                {where_clause}
                ORDER BY id DESC
                LIMIT %s
                """,
                (*params, limit),
            )
            rows = cursor.fetchall() or []
            return {"ok": True, "history": rows}
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


@app.get("/api/tags")
def list_tags(current_user: dict[str, str] = Depends(get_current_user)) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT state_key, payload_json, updated_at
                FROM tag_state
                WHERE username = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (current_user["username"],),
            )
            row = cursor.fetchone()
            if not row:
                return {"ok": True, "tag_state": {}, "tags": []}
            payload = {}
            if row.get("payload_json"):
                try:
                    decoded = json.loads(str(row["payload_json"]))
                    if isinstance(decoded, dict):
                        payload = decoded
                except Exception:
                    payload = {}
            return {
                "ok": True,
                "tag_state": payload,
                "tags": payload.get("samples") if isinstance(payload.get("samples"), list) else [],
                "updated_at": row.get("updated_at"),
            }
    finally:
        connection.close()


@app.post("/api/tags")
def upsert_tags(
    payload: TagStateRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    upsert_tag_state(
        current_user["username"],
        payload.payload,
        payload.state_key,
        user_id=int(current_user["id"]) if current_user.get("id") else None,
    )
    return {"ok": True}


@app.delete("/api/tags")
def delete_tags(
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    delete_tag_state(current_user["username"])
    return {"ok": True}


@app.get("/api/customer-variables")
def list_customer_variables(
    email: str | None = None,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    connection = _connect(DB_NAME)
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            if email:
                cursor.execute(
                    """
                    SELECT email, variables_json, updated_at
                    FROM customer_variables
                    WHERE username = %s AND email = %s
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                    (current_user["username"], email.strip().lower()),
                )
            else:
                cursor.execute(
                    """
                    SELECT email, variables_json, updated_at
                    FROM customer_variables
                    WHERE username = %s
                    ORDER BY updated_at DESC, id DESC
                    """,
                    (current_user["username"],),
                )
            rows = cursor.fetchall() or []
            items: list[dict[str, object]] = []
            for row in rows:
                payload: dict[str, Any] = {}
                raw = str(row.get("variables_json") or "")
                if raw:
                    try:
                        decoded = json.loads(raw)
                        if isinstance(decoded, dict):
                            payload = decoded
                    except Exception:
                        payload = {}
                items.append(
                    {
                        "email": row.get("email"),
                        "variables": payload,
                        "updated_at": row.get("updated_at"),
                    }
                )
            return {"ok": True, "items": items}
    finally:
        connection.close()


@app.post("/api/customer-variables")
def upsert_customer_variables_route(
    payload: CustomerVariableRequest,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    upsert_customer_variables(
        current_user["username"],
        payload.email,
        payload.variables,
        user_id=int(current_user["id"]) if current_user.get("id") else None,
    )
    return {"ok": True}


@app.delete("/api/customer-variables")
def delete_customer_variables_route(
    email: str | None = None,
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, object]:
    delete_customer_variables(current_user["username"], email=email)
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


def login(
    username: str,
    password: str,
    timeout: float = 5.0,
    device_fingerprint: str | None = None,
    device_name: str | None = None,
) -> dict:
    payload = {
        "username": username,
        "password": password,
    }
    if device_fingerprint:
        payload["device_fingerprint"] = device_fingerprint
    if device_name:
        payload["device_name"] = device_name
    request = urllib.request.Request(
        f"{API_BASE_URL}/api/login",
        data=json.dumps(payload).encode("utf-8"),
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


def get_tags(auth_token: str, timeout: float = 5.0) -> dict:
    return _authorized_request("GET", "/api/tags", auth_token, timeout=timeout)


def save_tags(
    auth_token: str,
    payload: dict[str, Any],
    state_key: str = "tag_state",
    timeout: float = 5.0,
) -> dict:
    return _authorized_request(
        "POST",
        "/api/tags",
        auth_token,
        {
            "state_key": state_key,
            "payload": payload,
        },
        timeout=timeout,
    )


def delete_tags(auth_token: str, timeout: float = 5.0) -> dict:
    return _authorized_request("DELETE", "/api/tags", auth_token, timeout=timeout)


def get_customer_variables(
    auth_token: str,
    email: str | None = None,
    timeout: float = 5.0,
) -> dict:
    query = {"email": email} if email else None
    return _authorized_request("GET", "/api/customer-variables", auth_token, timeout=timeout, query=query)


def save_customer_variables(
    auth_token: str,
    email: str,
    variables: dict[str, Any],
    timeout: float = 5.0,
) -> dict:
    return _authorized_request(
        "POST",
        "/api/customer-variables",
        auth_token,
        {
            "email": email,
            "variables": variables,
        },
        timeout=timeout,
    )


def delete_customer_variables(
    auth_token: str,
    email: str | None = None,
    timeout: float = 5.0,
) -> dict:
    query = {"email": email} if email else None
    return _authorized_request("DELETE", "/api/customer-variables", auth_token, timeout=timeout, query=query)


def list_admin_users(auth_token: str, timeout: float = 5.0) -> dict:
    return _authorized_request("GET", "/api/admin/users", auth_token, timeout=timeout)


def create_admin_user(
    auth_token: str,
    payload: dict[str, Any],
    timeout: float = 5.0,
) -> dict:
    return _authorized_request("POST", "/api/users", auth_token, payload, timeout=timeout)


def get_admin_user(auth_token: str, user_id: int, timeout: float = 5.0) -> dict:
    return _authorized_request("GET", f"/api/admin/users/{user_id}", auth_token, timeout=timeout)


def update_admin_user(
    auth_token: str,
    user_id: int,
    payload: dict[str, Any],
    timeout: float = 5.0,
) -> dict:
    return _authorized_request("PATCH", f"/api/admin/users/{user_id}", auth_token, payload, timeout=timeout)


def reset_admin_user_password(
    auth_token: str,
    user_id: int,
    password: str,
    timeout: float = 5.0,
) -> dict:
    return _authorized_request(
        "POST",
        f"/api/admin/users/{user_id}/reset-password",
        auth_token,
        {"password": password},
        timeout=timeout,
    )


def activate_admin_user(auth_token: str, user_id: int, timeout: float = 5.0) -> dict:
    return _authorized_request("POST", f"/api/admin/users/{user_id}/activate", auth_token, timeout=timeout)


def deactivate_admin_user(auth_token: str, user_id: int, timeout: float = 5.0) -> dict:
    return _authorized_request("POST", f"/api/admin/users/{user_id}/deactivate", auth_token, timeout=timeout)


def reset_admin_user_device(auth_token: str, user_id: int, timeout: float = 5.0) -> dict:
    return _authorized_request("POST", f"/api/admin/users/{user_id}/reset-device", auth_token, timeout=timeout)


def list_admin_activity(
    auth_token: str,
    username: str | None = None,
    limit: int = 200,
    timeout: float = 5.0,
) -> dict:
    query: dict[str, Any] = {"limit": limit}
    if username:
        query["username"] = username
    return _authorized_request("GET", "/api/admin/activity", auth_token, timeout=timeout, query=query)


def list_admin_login_history(
    auth_token: str,
    username: str | None = None,
    limit: int = 200,
    timeout: float = 5.0,
) -> dict:
    query: dict[str, Any] = {"limit": limit}
    if username:
        query["username"] = username
    return _authorized_request("GET", "/api/admin/login-history", auth_token, timeout=timeout, query=query)
