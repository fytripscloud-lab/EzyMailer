from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response

from app.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import is_valid_job_id, new_job_id, sanitize_filename
from app.models.schemas import (
    JobStatus,
    ProgressResponse,
    ResultRow,
    ResultsPage,
    StartRequest,
    SummaryReport,
    UploadResponse,
)
from app.services import exporter
from app.services.file_parser import (
    UnsupportedFileError,
    content_matches_extension,
    detect_email_column,
    list_sheets,
    read_sheet,
)
from app.services.job_store import JobStore
from app.services.report import compute_summary, generate_pdf_report
from app.services.validator_engine import ValidationEngine
from app.workers import job_runner

router = APIRouter(prefix="/api/v1/bulk-validator", tags=["bulk-validator"])

_settings_for_limits = get_settings()


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_store_dep(request: Request) -> JobStore:
    return request.app.state.store


def get_engine_dep(request: Request) -> ValidationEngine:
    return request.app.state.engine


def _get_job_or_404(store: JobStore, job_id: str) -> dict:
    if not is_valid_job_id(job_id) or not store.job_exists(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    return store.load_metadata(job_id)


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(_settings_for_limits.upload_rate_limit)
async def upload_file(request: Request, file: UploadFile = File(...)):
    settings = get_settings_dep(request)
    store = get_store_dep(request)

    original_name = sanitize_filename(file.filename or "upload")
    extension = Path(original_name).suffix.lower()
    if extension not in settings.allowed_extension_list:
        raise HTTPException(status_code=400, detail=f"unsupported file extension: {extension}")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="uploaded file is empty")
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="file exceeds maximum upload size")
    if not content_matches_extension(extension, content):
        raise HTTPException(status_code=400, detail="file content does not match its extension")

    job_id = new_job_id()
    store.uploads_dir(job_id).mkdir(parents=True, exist_ok=True)
    upload_path = store.uploads_dir(job_id) / f"original{extension}"
    upload_path.write_bytes(content)

    try:
        sheet_names = list_sheets(upload_path)
        selected_sheet = sheet_names[0]
        df = read_sheet(upload_path, selected_sheet)
    except UnsupportedFileError as exc:
        store.delete_job(job_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(df) > settings.max_rows:
        store.delete_job(job_id)
        raise HTTPException(
            status_code=400,
            detail=f"file has {len(df)} rows, exceeding the limit of {settings.max_rows}",
        )

    detected_column = detect_email_column(df)

    metadata = {
        "job_id": job_id,
        "original_filename": original_name,
        "upload_path": str(upload_path),
        "extension": extension,
        "size_bytes": len(content),
        "sheet_names": sheet_names,
        "selected_sheet": selected_sheet,
        "available_columns": list(df.columns),
        "detected_email_column": detected_column,
        "total_records": len(df),
        "status": JobStatus.UPLOADED.value,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    store.init_job(job_id, metadata)

    return UploadResponse(
        job_id=job_id,
        filename=original_name,
        size_bytes=len(content),
        total_records=len(df),
        detected_email_column=detected_column,
        available_columns=list(df.columns),
        sheet_names=sheet_names,
        selected_sheet=selected_sheet,
        requires_column_selection=detected_column is None,
    )


@router.post("/start/{job_id}", response_model=ProgressResponse)
@limiter.limit(_settings_for_limits.start_rate_limit)
async def start_validation(
    request: Request,
    job_id: str,
    payload: StartRequest | None = Body(default=None),
):
    settings = get_settings_dep(request)
    store = get_store_dep(request)
    engine = get_engine_dep(request)
    payload = payload or StartRequest()

    metadata = _get_job_or_404(store, job_id)
    if job_runner.is_running(job_id):
        raise HTTPException(status_code=409, detail="job is already validating")

    chosen_sheet = payload.sheet_name or metadata["selected_sheet"]
    if chosen_sheet != metadata["selected_sheet"]:
        df = read_sheet(Path(metadata["upload_path"]), chosen_sheet)
        metadata["available_columns"] = list(df.columns)
        metadata["selected_sheet"] = chosen_sheet

    chosen_column = payload.email_column or metadata.get("detected_email_column")
    if not chosen_column or chosen_column not in metadata["available_columns"]:
        raise HTTPException(status_code=400, detail="a valid email_column must be specified")

    store.save_metadata(job_id, metadata)
    job_runner.start_job(job_id, settings, store, engine, chosen_column, chosen_sheet)

    total = metadata["total_records"]
    return ProgressResponse(
        job_id=job_id,
        status=JobStatus.VALIDATING,
        total=total,
        processed=0,
        remaining=total,
        valid=0,
        invalid=0,
        risky=0,
        unknown=0,
        percent=0.0,
        emails_per_second=0.0,
        eta_seconds=None,
        started_at=None,
        completed_at=None,
    )


@router.get("/progress/{job_id}", response_model=ProgressResponse)
async def get_progress(request: Request, job_id: str):
    store = get_store_dep(request)
    metadata = _get_job_or_404(store, job_id)
    progress = store.load_progress(job_id)
    total = progress.get("total", metadata.get("total_records", 0))

    return ProgressResponse(
        job_id=job_id,
        status=JobStatus(progress.get("status", metadata["status"])),
        total=total,
        processed=progress.get("processed", 0),
        remaining=progress.get("remaining", total),
        valid=progress.get("valid", 0),
        invalid=progress.get("invalid", 0),
        risky=progress.get("risky", 0),
        unknown=progress.get("unknown", 0),
        percent=progress.get("percent", 0.0),
        emails_per_second=progress.get("emails_per_second", 0.0),
        eta_seconds=progress.get("eta_seconds"),
        started_at=progress.get("started_at") or metadata.get("started_at"),
        completed_at=progress.get("completed_at") or metadata.get("completed_at"),
        error=progress.get("error") or metadata.get("error"),
        recent_activity=progress.get("recent_activity", []),
    )


@router.get("/results/{job_id}", response_model=ResultsPage)
async def get_results(
    request: Request,
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    filter: str = Query("all"),
    search: str | None = Query(None),
):
    store = get_store_dep(request)
    _get_job_or_404(store, job_id)
    rows, total = store.query_results(job_id, page, page_size, filter, search)
    total_pages = (total + page_size - 1) // page_size if page_size else 0

    return ResultsPage(
        job_id=job_id,
        page=page,
        page_size=page_size,
        total_rows=total,
        total_pages=total_pages,
        filter=filter,
        search=search,
        rows=[ResultRow(**r) for r in rows],
    )


@router.get("/report/{job_id}", response_model=SummaryReport)
async def get_report(request: Request, job_id: str):
    store = get_store_dep(request)
    metadata = _get_job_or_404(store, job_id)
    summary = store.load_summary(job_id)
    if summary is None:
        if metadata["status"] not in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value):
            raise HTTPException(status_code=409, detail="validation has not completed yet")
        summary = compute_summary(store, job_id, metadata)
        store.save_summary(job_id, summary)
    return SummaryReport(**summary)


@router.get("/export/{job_id}")
async def export_results(
    request: Request,
    job_id: str,
    format: str = Query("xlsx", pattern="^(xlsx|csv|pdf)$"),
    filter: str = Query("all"),
    search: str | None = Query(None),
):
    store = get_store_dep(request)
    metadata = _get_job_or_404(store, job_id)
    if metadata["status"] not in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value):
        raise HTTPException(status_code=409, detail="validation has not completed yet")

    # A filter/search narrows the export to exactly what the Results table is
    # currently showing; it's query-specific so it's built on demand rather
    # than cached to disk like the full "All" exports below. PDF is always
    # the overall summary report regardless of table filtering.
    is_scoped = format != "pdf" and (filter.lower() != "all" or bool(search))

    if format == "xlsx":
        if is_scoped:
            content = exporter.build_filtered_xlsx(store, job_id, filter, search)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": 'attachment; filename="validation_results_filtered.xlsx"'},
            )
        out_path = store.exports_dir(job_id) / "results.xlsx"
        if not out_path.exists():
            exporter.export_xlsx(store, job_id, out_path)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        download_name = "validation_results.xlsx"
    elif format == "csv":
        if is_scoped:
            content = exporter.build_filtered_csv(store, job_id, filter, search)
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": 'attachment; filename="validation_results_filtered.csv"'},
            )
        out_path = store.exports_dir(job_id) / "results.csv"
        if not out_path.exists():
            exporter.export_csv(store, job_id, out_path)
        media_type = "text/csv"
        download_name = "validation_results.csv"
    else:
        out_path = store.reports_dir(job_id) / "report.pdf"
        if not out_path.exists():
            summary = store.load_summary(job_id) or compute_summary(store, job_id, metadata)
            generate_pdf_report(summary, metadata, out_path)
        media_type = "application/pdf"
        download_name = "validation_report.pdf"

    return FileResponse(path=out_path, media_type=media_type, filename=download_name)


@router.post("/cancel/{job_id}")
async def cancel_job(request: Request, job_id: str):
    store = get_store_dep(request)
    _get_job_or_404(store, job_id)
    if not job_runner.request_cancel(job_id):
        raise HTTPException(status_code=409, detail="job is not currently running")
    return {"job_id": job_id, "cancel_requested": True}


@router.delete("/job/{job_id}")
async def delete_job(request: Request, job_id: str):
    store = get_store_dep(request)
    _get_job_or_404(store, job_id)
    job_runner.request_cancel(job_id)
    store.delete_job(job_id)
    return {"job_id": job_id, "deleted": True}
