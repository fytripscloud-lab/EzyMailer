import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.v1.bulk_validator import router as bulk_validator_router
from app.api.v1.system import router as system_router
from app.config import get_settings
from app.core.auth import verify_token
from app.core.rate_limit import limiter
from app.services.cleanup import cleanup_loop, recover_orphaned_jobs
from app.services.job_store import JobStore
from app.services.validator_engine import ValidationEngine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.store = JobStore(settings)
    app.state.engine = ValidationEngine(settings)

    recovered = recover_orphaned_jobs(app.state.store)
    if recovered:
        logging.getLogger(__name__).warning(
            "startup: marked %d job(s) as failed - they were left mid-validation by a previous server process",
            recovered,
        )

    cleanup_task = asyncio.create_task(cleanup_loop(settings, app.state.store))
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Bulk Email Validator API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(status_code=429, content={"detail": "rate limit exceeded"}),
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bulk_validator_router, dependencies=[Depends(verify_token)])
app.include_router(system_router, dependencies=[Depends(verify_token)])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/session/local")
async def local_session() -> dict[str, str]:
    """Lets the frontend auto-login instead of showing the fallback login
    form, when this backend is running bundled inside EzyMailer's own
    desktop process (the only thing that ever starts it - see
    ensure_validator_server() in main.py) and that app's user is already
    signed in. Deliberately unauthenticated: its whole purpose is to hand
    out a token before one exists."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        raise HTTPException(status_code=404, detail="Not running inside the EzyMailer desktop app.")

    main_window = getattr(QApplication.instance(), "main_window", None)
    state = getattr(main_window, "state", None)
    if not state or not getattr(state, "logged_in", False) or not getattr(state, "auth_token", None):
        raise HTTPException(status_code=401, detail="Not signed in to EzyMailer.")

    return {"token": state.auth_token}


def _frontend_static_dir() -> Path:
    """Where the frontend's static export (`next build` with output:
    "export") lives. When PyInstaller-bundled into the desktop app, it's
    unpacked next to this module under _MEIPASS; in dev it's the sibling
    frontend/out/ produced by `npm run build`."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "validator_frontend"
    return Path(__file__).resolve().parents[2] / "frontend" / "out"


# Mounted last so it never shadows the /api/v1/* and /health routes above -
# Starlette matches routes in registration order, and a mount at "/" would
# otherwise swallow everything registered after it. Only mounted when the
# static export actually exists, so a plain `uvicorn app.main:app` for API
# development (frontend served separately via `npm run dev`) still works.
_static_dir = _frontend_static_dir()
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="validator-frontend")
