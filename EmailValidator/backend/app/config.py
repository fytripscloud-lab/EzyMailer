from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    imported_dir: str = "imported"
    job_retention_hours: int = 24
    cleanup_interval_minutes: int = 30

    max_upload_size_mb: int = 25
    max_rows: int = 100_000
    allowed_extensions: str = ".xlsx,.xls,.csv"

    dns_concurrency: int = 20
    # Kept low by default: real mailbox providers (Gmail/Outlook/Yahoo) rate-limit
    # and reputation-flag IPs that open many concurrent RCPT-only connections.
    # Raise this gradually on a VPS with its own reputation/PTR record, not blindly.
    smtp_concurrency: int = 5
    dns_timeout_seconds: int = 5
    smtp_timeout_seconds: int = 8
    smtp_retries: int = 1
    dns_cache_ttl_seconds: int = 600
    smtp_helo_domain: str = "example.com"
    smtp_from_address: str = "verify@example.com"
    enable_smtp_check: bool = True
    enable_catch_all_check: bool = True
    diagnostics_test_domain: str = "gmail.com"

    progress_flush_interval: int = 25
    batch_size: int = 200

    upload_rate_limit: str = "10/minute"
    start_rate_limit: str = "10/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extension_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def uploads_dir(self) -> Path:
        return self.base_dir / self.imported_dir / "uploads"

    @property
    def processing_dir(self) -> Path:
        return self.base_dir / self.imported_dir / "processing"

    @property
    def exports_dir(self) -> Path:
        return self.base_dir / self.imported_dir / "exports"

    @property
    def reports_dir(self) -> Path:
        return self.base_dir / self.imported_dir / "reports"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for d in (settings.uploads_dir, settings.processing_dir, settings.exports_dir, settings.reports_dir):
        d.mkdir(parents=True, exist_ok=True)
    return settings
