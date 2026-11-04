from datetime import datetime, timedelta, timezone

import pytest

from app.services.cleanup import ORPHANED_JOB_ERROR, cleanup_once, recover_orphaned_jobs
from app.services.job_store import JobStore


@pytest.mark.asyncio
async def test_cleanup_removes_expired_jobs_and_keeps_fresh_ones(test_settings):
    store = JobStore(test_settings)

    old_job = "d" * 32
    fresh_job = "e" * 32

    old_time = (datetime.now(timezone.utc) - timedelta(hours=test_settings.job_retention_hours + 5)).isoformat()
    fresh_time = datetime.now(timezone.utc).isoformat()

    store.init_job(old_job, {"status": "completed", "completed_at": old_time})
    store.init_job(fresh_job, {"status": "completed", "completed_at": fresh_time})

    removed = await cleanup_once(test_settings, store)

    assert removed == 1
    assert store.job_exists(old_job) is False
    assert store.job_exists(fresh_job) is True

    store.delete_job(fresh_job)


@pytest.mark.asyncio
async def test_cleanup_skips_jobs_without_timestamps(test_settings):
    store = JobStore(test_settings)
    job_id = "f" * 32
    store.init_job(job_id, {"status": "uploaded"})

    removed = await cleanup_once(test_settings, store)

    assert removed == 0
    assert store.job_exists(job_id) is True
    store.delete_job(job_id)


def test_recover_orphaned_jobs_marks_stuck_validating_jobs_failed(test_settings):
    store = JobStore(test_settings)

    orphaned_job = "1" * 32
    uploaded_job = "2" * 32
    completed_job = "3" * 32

    store.init_job(orphaned_job, {"status": "validating", "started_at": "2026-01-01T00:00:00+00:00"})
    store.save_progress(orphaned_job, {"status": "validating", "processed": 1200, "total": 4998})

    store.init_job(uploaded_job, {"status": "uploaded"})
    store.init_job(completed_job, {"status": "completed", "completed_at": "2026-01-01T00:00:05+00:00"})

    recovered = recover_orphaned_jobs(store)

    assert recovered == 1

    metadata = store.load_metadata(orphaned_job)
    assert metadata["status"] == "failed"
    assert metadata["error"] == ORPHANED_JOB_ERROR

    progress = store.load_progress(orphaned_job)
    assert progress["status"] == "failed"
    assert progress["error"] == ORPHANED_JOB_ERROR
    assert progress["processed"] == 1200  # last-seen progress preserved, not wiped

    # Untouched jobs stay exactly as they were.
    assert store.load_metadata(uploaded_job)["status"] == "uploaded"
    assert store.load_metadata(completed_job)["status"] == "completed"

    store.delete_job(orphaned_job)
    store.delete_job(uploaded_job)
    store.delete_job(completed_job)


def test_recover_orphaned_jobs_is_a_noop_when_nothing_stuck(test_settings):
    store = JobStore(test_settings)
    job_id = "4" * 32
    store.init_job(job_id, {"status": "completed", "completed_at": "2026-01-01T00:00:05+00:00"})

    assert recover_orphaned_jobs(store) == 0

    store.delete_job(job_id)


def test_server_startup_recovers_orphaned_jobs(test_settings):
    """An end-to-end check that app startup (not just the helper function in
    isolation) actually runs recovery - simulates a job left 'validating' on
    disk by a server process that died, then a fresh server starting up."""
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.conftest import make_token

    store = JobStore(test_settings)
    orphaned_job = "5" * 32
    store.init_job(orphaned_job, {"status": "validating", "started_at": "2026-01-01T00:00:00+00:00"})
    store.save_progress(orphaned_job, {"status": "validating", "processed": 10, "total": 100})

    # get_settings() is lru_cached and test_settings already populated that
    # cache, so the lifespan's own get_settings() call below returns the same
    # instance - the app.state.store it builds points at this same directory.
    with TestClient(app) as client:
        client.headers.update({"Authorization": f"Bearer {make_token()}"})
        resp = client.get(f"/api/v1/bulk-validator/progress/{orphaned_job}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert "server restart" in data["error"]

    store.delete_job(orphaned_job)
