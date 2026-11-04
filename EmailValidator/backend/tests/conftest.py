import io
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.core.auth import JWT_ALGORITHM, JWT_SECRET
from app.core.rate_limit import limiter
from app.services.job_store import JobStore
from app.services.validator_engine import ValidationEngine


def make_token(sub: str = "test-user", role: str = "admin", secret: str = JWT_SECRET) -> str:
    return jwt.encode({"sub": sub, "role": role}, secret, algorithm=JWT_ALGORITHM)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    limiter.reset()


@pytest.fixture
def tmp_imported_dir() -> Iterator[Path]:
    d = Path(tempfile.mkdtemp(prefix="email_validator_test_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def test_settings(tmp_imported_dir: Path, monkeypatch) -> Settings:
    get_settings.cache_clear()
    monkeypatch.setenv("IMPORTED_DIR", str(tmp_imported_dir))
    monkeypatch.setenv("ENABLE_SMTP_CHECK", "false")
    monkeypatch.setenv("ENABLE_CATCH_ALL_CHECK", "false")
    monkeypatch.setenv("JOB_RETENTION_HOURS", "24")
    settings = get_settings()
    # Settings.base_dir is derived from the app package location, not env,
    # so point all storage dirs explicitly at the temp directory for isolation.
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.processing_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    yield settings
    get_settings.cache_clear()


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as c:
        c.app.state.settings = test_settings
        c.app.state.store = JobStore(test_settings)
        c.app.state.engine = ValidationEngine(test_settings)
        c.headers.update({"Authorization": f"Bearer {make_token()}"})
        yield c


def make_csv_bytes(rows: list[dict]) -> bytes:
    import csv

    buf = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["Name", "Email"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")
