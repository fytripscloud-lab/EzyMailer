import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.services.job_store import JobStore

logger = logging.getLogger(__name__)


async def cleanup_once(settings: Settings, store: JobStore) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.job_retention_hours)
    removed = 0
    for job_id in store.all_job_ids():
        try:
            metadata = store.load_metadata(job_id)
        except Exception:
            continue

        reference_str = metadata.get("completed_at") or metadata.get("uploaded_at")
        if not reference_str:
            continue
        try:
            reference = datetime.fromisoformat(reference_str)
        except ValueError:
            continue
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        if reference < cutoff:
            store.delete_job(job_id)
            removed += 1
            logger.info("cleanup: removed expired job %s", job_id)
    return removed


ORPHANED_JOB_ERROR = "Validation was interrupted by a server restart. Please start validation again."


def recover_orphaned_jobs(store: JobStore) -> int:
    """Run once at startup. A job's background validation task lives only in
    the process memory of whichever server instance started it - job_runner's
    `_running_tasks`/`_cancel_flags` dicts are in-memory, not persisted. If
    the server restarts while a job is mid-validation, its task is gone but
    its on-disk status still says "validating" with whatever progress it last
    saved, so the frontend would poll it forever without any sign that
    nothing is actually processing it. Since this runs before anything else
    on a fresh process, any job still marked "validating" at this point is
    unambiguously orphaned - mark it failed instead of leaving it stuck.
    """
    recovered = 0
    for job_id in store.all_job_ids():
        try:
            metadata = store.load_metadata(job_id)
        except Exception:
            continue
        if metadata.get("status") != "validating":
            continue

        metadata["status"] = "failed"
        metadata["error"] = ORPHANED_JOB_ERROR
        store.save_metadata(job_id, metadata)

        progress = store.load_progress(job_id)
        progress["status"] = "failed"
        progress["error"] = ORPHANED_JOB_ERROR
        store.save_progress(job_id, progress)

        recovered += 1
        logger.warning("recovered orphaned job %s (was stuck in 'validating')", job_id)
    return recovered


async def cleanup_loop(settings: Settings, store: JobStore) -> None:
    interval_seconds = max(settings.cleanup_interval_minutes, 1) * 60
    while True:
        try:
            await cleanup_once(settings, store)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("cleanup loop iteration failed")
        await asyncio.sleep(interval_seconds)
