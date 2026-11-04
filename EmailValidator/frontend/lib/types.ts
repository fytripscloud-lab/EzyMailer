export type JobStatus = "uploaded" | "validating" | "completed" | "cancelled" | "failed";
export type FinalStatus = "valid" | "invalid" | "risky" | "unknown";
export type TriState = "yes" | "no" | "unknown";
export type ResultFilter = "all" | FinalStatus | "disposable";

export interface UploadResponse {
  job_id: string;
  filename: string;
  size_bytes: number;
  total_records: number;
  detected_email_column: string | null;
  available_columns: string[];
  sheet_names: string[];
  selected_sheet: string;
  requires_column_selection: boolean;
}

export interface ActivityEntry {
  email: string;
  status: FinalStatus;
  timestamp: string;
}

export interface ProgressResponse {
  job_id: string;
  status: JobStatus;
  total: number;
  processed: number;
  remaining: number;
  valid: number;
  invalid: number;
  risky: number;
  unknown: number;
  percent: number;
  emails_per_second: number;
  eta_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
  error?: string | null;
  recent_activity: ActivityEntry[];
}

export interface ResultRow {
  row_no: number;
  original: Record<string, string>;
  email: string;
  syntax_valid: boolean;
  domain_valid: boolean;
  mx_found: boolean;
  smtp: string;
  disposable: boolean;
  free_provider: boolean;
  role_based: boolean;
  catch_all: TriState;
  final_status: FinalStatus;
  is_duplicate: boolean;
}

export interface ResultsPage {
  job_id: string;
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
  filter: string;
  search: string | null;
  rows: ResultRow[];
}

export interface DiagnosticsResponse {
  checked_at: string;
  backend: string;
  dns: "ok" | "failed";
  dns_detail: string;
  smtp_port_25: "open" | "blocked" | "timeout" | "unknown" | "disabled";
  smtp_detail: string;
  smtp_check_enabled: boolean;
  catch_all_check_enabled: boolean;
  smtp_concurrency: number;
  dns_concurrency: number;
  max_upload_size_mb: number;
  max_rows: number;
  job_retention_hours: number;
}

export interface SummaryReport {
  job_id: string;
  total_uploaded: number;
  unique_emails: number;
  duplicate_emails: number;
  valid_count: number;
  invalid_count: number;
  risky_count: number;
  unknown_count: number;
  disposable_count: number;
  free_provider_count: number;
  role_based_count: number;
  success_percent: number;
  validation_duration_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
}
