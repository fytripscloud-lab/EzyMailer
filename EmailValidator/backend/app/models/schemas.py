from enum import Enum
from typing import Any

from pydantic import BaseModel


class JobStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class FinalStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    UNKNOWN = "unknown"


class TriState(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    size_bytes: int
    total_records: int
    detected_email_column: str | None
    available_columns: list[str]
    sheet_names: list[str]
    selected_sheet: str
    requires_column_selection: bool


class StartRequest(BaseModel):
    email_column: str | None = None
    sheet_name: str | None = None


class ActivityEntry(BaseModel):
    email: str
    status: FinalStatus
    timestamp: str


class ProgressResponse(BaseModel):
    job_id: str
    status: JobStatus
    total: int
    processed: int
    remaining: int
    valid: int
    invalid: int
    risky: int
    unknown: int
    percent: float
    emails_per_second: float
    eta_seconds: float | None
    started_at: str | None
    completed_at: str | None
    error: str | None = None
    recent_activity: list[ActivityEntry] = []


class ResultRow(BaseModel):
    row_no: int
    original: dict[str, Any]
    email: str
    syntax_valid: bool
    domain_valid: bool
    mx_found: bool
    smtp: str
    disposable: bool
    free_provider: bool
    role_based: bool
    catch_all: TriState
    final_status: FinalStatus
    is_duplicate: bool


class ResultsPage(BaseModel):
    job_id: str
    page: int
    page_size: int
    total_rows: int
    total_pages: int
    filter: str
    search: str | None
    rows: list[ResultRow]


class DiagnosticsResponse(BaseModel):
    checked_at: str
    backend: str
    dns: str
    dns_detail: str
    smtp_port_25: str
    smtp_detail: str
    smtp_check_enabled: bool
    catch_all_check_enabled: bool
    smtp_concurrency: int
    dns_concurrency: int
    max_upload_size_mb: int
    max_rows: int
    job_retention_hours: int


class SummaryReport(BaseModel):
    job_id: str
    total_uploaded: int
    unique_emails: int
    duplicate_emails: int
    valid_count: int
    invalid_count: int
    risky_count: int
    unknown_count: int
    disposable_count: int
    free_provider_count: int
    role_based_count: int
    success_percent: float
    validation_duration_seconds: float | None
    started_at: str | None
    completed_at: str | None
