import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.services.file_parser import extract_email_records, read_sheet
from app.services.job_store import JobStore
from app.services.report import compute_summary
from app.services.validator_engine import ValidationEngine

logger = logging.getLogger(__name__)

_cancel_flags: dict[str, bool] = {}
_running_tasks: dict[str, asyncio.Task] = {}


def is_running(job_id: str) -> bool:
    task = _running_tasks.get(job_id)
    return task is not None and not task.done()


def request_cancel(job_id: str) -> bool:
    if is_running(job_id):
        _cancel_flags[job_id] = True
        return True
    return False


def start_job(
    job_id: str,
    settings: Settings,
    store: JobStore,
    engine: ValidationEngine,
    email_column: str,
    sheet_name: str | None,
) -> None:
    task = asyncio.create_task(_run_job(job_id, settings, store, engine, email_column, sheet_name))
    _running_tasks[job_id] = task


async def _run_job(
    job_id: str,
    settings: Settings,
    store: JobStore,
    engine: ValidationEngine,
    email_column: str,
    sheet_name: str | None,
) -> None:
    _cancel_flags[job_id] = False
    metadata = store.load_metadata(job_id)

    try:
        upload_path = Path(metadata["upload_path"])
        df = read_sheet(upload_path, sheet_name)
        records = extract_email_records(df, email_column)
        total = len(records)

        store.truncate_results(job_id)

        counts = {"valid": 0, "invalid": 0, "risky": 0, "unknown": 0}
        processed = 0
        recent_activity: deque[dict] = deque(maxlen=14)
        started_at = datetime.now(timezone.utc)
        start_time = time.monotonic()

        metadata["status"] = "validating"
        metadata["email_column"] = email_column
        metadata["sheet_name"] = sheet_name
        metadata["started_at"] = started_at.isoformat()
        store.save_metadata(job_id, metadata)

        def flush_progress(status: str = "validating") -> None:
            elapsed = max(time.monotonic() - start_time, 1e-6)
            speed = processed / elapsed
            remaining = total - processed
            eta = remaining / speed if speed > 0 else None
            store.save_progress(
                job_id,
                {
                    "status": status,
                    "total": total,
                    "processed": processed,
                    "remaining": remaining,
                    **counts,
                    "percent": round((processed / total * 100) if total else 100.0, 2),
                    "emails_per_second": round(speed, 2),
                    "eta_seconds": round(eta, 1) if eta is not None else None,
                    "started_at": started_at.isoformat(),
                    "completed_at": None,
                    "error": None,
                    "recent_activity": list(recent_activity),
                },
            )

        flush_progress()

        async def process_record(record: dict) -> tuple[dict, object]:
            nonlocal processed
            check = await engine.validate_one(record["email"])
            # Counts/activity update the instant each check resolves (not in
            # original row order) so progress feels live; the actual
            # results.jsonl write still happens in original row order below.
            processed += 1
            counts[check.final_status] += 1
            recent_activity.append(
                {
                    "email": check.email or record["email"],
                    "status": check.final_status,
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                }
            )
            if processed % settings.progress_flush_interval == 0:
                flush_progress()
            return record, check

        for i in range(0, total, settings.batch_size):
            if _cancel_flags.get(job_id):
                break
            batch = records[i : i + settings.batch_size]
            # Validation runs concurrently within the batch, but results are
            # written back out in original row order (not completion order)
            # so results.jsonl always matches the source spreadsheet order.
            batch_results = await asyncio.gather(*(process_record(r) for r in batch))
            for record, check in batch_results:
                store.append_result(
                    job_id,
                    {
                        "row_no": record["row_no"],
                        "original": record["original"],
                        "email": check.email or record["email"],
                        "syntax_valid": check.syntax_valid,
                        "domain_valid": check.domain_valid,
                        "mx_found": check.mx_found,
                        "smtp": check.smtp,
                        "disposable": check.disposable,
                        "free_provider": check.free_provider,
                        "role_based": check.role_based,
                        "catch_all": check.catch_all,
                        "final_status": check.final_status,
                        "is_duplicate": record["is_duplicate"],
                    },
                )
            flush_progress()

        cancelled = _cancel_flags.get(job_id, False)
        completed_at = datetime.now(timezone.utc)
        final_status = "cancelled" if cancelled else "completed"
        flush_progress(status=final_status)

        metadata["status"] = final_status
        metadata["completed_at"] = completed_at.isoformat()
        store.save_metadata(job_id, metadata)

        summary = compute_summary(store, job_id, metadata)
        store.save_summary(job_id, summary)

    except Exception as exc:  # noqa: BLE001
        logger.exception("job %s failed", job_id)
        try:
            progress = store.load_progress(job_id)
            progress["status"] = "failed"
            progress["error"] = str(exc)
            store.save_progress(job_id, progress)
        except Exception:
            pass
        metadata["status"] = "failed"
        metadata["error"] = str(exc)
        store.save_metadata(job_id, metadata)
    finally:
        _cancel_flags.pop(job_id, None)
