import os

import jwt
from fastapi import Header, HTTPException, Query, status

# Must match EZYM_MAILER_JWT_SECRET / the HS256 scheme in ezymailer's own
# backend/local_api.py so a token issued by the main app's /api/login is
# accepted here too - this is what lets "Mail Validator" open already signed in.
JWT_SECRET = os.getenv("EZYM_MAILER_JWT_SECRET", "ezymailer-local-development-secret")
JWT_ALGORITHM = "HS256"


def verify_token(
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
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    return {"username": str(payload.get("sub", "")), "role": str(payload.get("role", ""))}
