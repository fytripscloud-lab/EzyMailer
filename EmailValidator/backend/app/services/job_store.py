import json
import shutil
from pathlib import Path
from typing import Any, Iterator

from app.config import Settings


class JobStore:
    """All job state lives on the filesystem under imported/ - no database.
    job_id (a uuid4 hex string) is the only value ever used to build paths."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def uploads_dir(self, job_id: str) -> Path:
        return self.settings.uploads_dir / job_id

    def processing_dir(self, job_id: str) -> Path:
        return self.settings.processing_dir / job_id

    def exports_dir(self, job_id: str) -> Path:
        return self.settings.exports_dir / job_id

    def reports_dir(self, job_id: str) -> Path:
        return self.settings.reports_dir / job_id

    def metadata_path(self, job_id: str) -> Path:
        return self.processing_dir(job_id) / "metadata.json"

    def progress_path(self, job_id: str) -> Path:
        return self.processing_dir(job_id) / "progress.json"

    def results_path(self, job_id: str) -> Path:
        return self.processing_dir(job_id) / "results.jsonl"

    def summary_path(self, job_id: str) -> Path:
        return self.processing_dir(job_id) / "summary.json"

    def job_exists(self, job_id: str) -> bool:
        return self.metadata_path(job_id).exists()

    def init_job(self, job_id: str, metadata: dict[str, Any]) -> None:
        self.uploads_dir(job_id).mkdir(parents=True, exist_ok=True)
        self.processing_dir(job_id).mkdir(parents=True, exist_ok=True)
        self.save_metadata(job_id, metadata)

    def save_metadata(self, job_id: str, metadata: dict[str, Any]) -> None:
        self.metadata_path(job_id).write_text(json.dumps(metadata, indent=2))

    def load_metadata(self, job_id: str) -> dict[str, Any]:
        return json.loads(self.metadata_path(job_id).read_text())

    def save_progress(self, job_id: str, progress: dict[str, Any]) -> None:
        self.progress_path(job_id).write_text(json.dumps(progress, indent=2))

    def load_progress(self, job_id: str) -> dict[str, Any]:
        path = self.progress_path(job_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def truncate_results(self, job_id: str) -> None:
        self.results_path(job_id).write_text("")

    def append_result(self, job_id: str, row: dict[str, Any]) -> None:
        with self.results_path(job_id).open("a") as f:
            f.write(json.dumps(row) + "\n")

    def iter_results(self, job_id: str) -> Iterator[dict[str, Any]]:
        path = self.results_path(job_id)
        if not path.exists():
            return
        with path.open("r") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def _matching_results(self, job_id: str, filter_: str | None, search: str | None) -> list[dict[str, Any]]:
        filter_ = (filter_ or "all").lower()
        search = (search or "").strip().lower()
        matched: list[dict[str, Any]] = []
        for row in self.iter_results(job_id):
            if filter_ != "all":
                if filter_ == "disposable":
                    if not row.get("disposable"):
                        continue
                elif row.get("final_status") != filter_:
                    continue
            if search and search not in row.get("email", "").lower():
                continue
            matched.append(row)
        return matched

    def query_results(
        self, job_id: str, page: int, page_size: int, filter_: str | None, search: str | None
    ) -> tuple[list[dict[str, Any]], int]:
        matched = self._matching_results(job_id, filter_, search)
        total = len(matched)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return matched[start:end], total

    def query_all_results(self, job_id: str, filter_: str | None, search: str | None) -> list[dict[str, Any]]:
        """Unpaginated version of query_results, for exports that need every
        row matching the current filter/search rather than one page of it."""
        return self._matching_results(job_id, filter_, search)

    def save_summary(self, job_id: str, summary: dict[str, Any]) -> None:
        self.summary_path(job_id).write_text(json.dumps(summary, indent=2))

    def load_summary(self, job_id: str) -> dict[str, Any] | None:
        path = self.summary_path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def delete_job(self, job_id: str) -> None:
        for d in (
            self.uploads_dir(job_id),
            self.processing_dir(job_id),
            self.exports_dir(job_id),
            self.reports_dir(job_id),
        ):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

    def all_job_ids(self) -> set[str]:
        base = self.settings.processing_dir
        if not base.exists():
            return set()
        return {p.name for p in base.iterdir() if p.is_dir()}
