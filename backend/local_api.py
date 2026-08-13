from __future__ import annotations

import json
import hashlib
import hmac
import secrets
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import jwt
import pymysql
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn


API_HOST = "127.0.0.1"
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
def login(payload: LoginRequest) -> dict[str, object]:
    user = _authenticate(payload.username.strip(), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

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
