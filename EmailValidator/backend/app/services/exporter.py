import csv
import io
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.job_store import JobStore

SHEET_FILTERS: dict[str, str | None] = {
    "All Results": None,
    "Valid Emails": "valid",
    "Invalid Emails": "invalid",
    "Risky Emails": "risky",
    "Unknown Emails": "unknown",
}


def _flatten(row: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = dict(row.get("original", {}))
    flat.update(
        {
            "Row No.": row["row_no"],
            "Email": row["email"],
            "Syntax": "Valid" if row["syntax_valid"] else "Invalid",
            "Domain": "Valid" if row["domain_valid"] else "Invalid",
            "MX Record": "Found" if row["mx_found"] else "Not Found",
            "SMTP": str(row["smtp"]).capitalize(),
            "Disposable": "Yes" if row["disposable"] else "No",
            "Free Provider": "Yes" if row["free_provider"] else "No",
            "Role Based": "Yes" if row["role_based"] else "No",
            "Catch-All": str(row["catch_all"]).capitalize(),
            "Final Status": str(row["final_status"]).capitalize(),
            "Duplicate": "Yes" if row["is_duplicate"] else "No",
        }
    )
    return flat


def _flat_rows(store: JobStore, job_id: str) -> list[dict[str, Any]]:
    return [_flatten(r) for r in store.iter_results(job_id)]


def export_xlsx(store: JobStore, job_id: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flat_rows = _flat_rows(store, job_id)
    df_all = pd.DataFrame(flat_rows)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_all.to_excel(writer, sheet_name="All Results", index=False)
        for sheet_name, status in SHEET_FILTERS.items():
            if status is None:
                continue
            subset = [r for r in flat_rows if r["Final Status"].lower() == status]
            df_subset = pd.DataFrame(subset) if subset else pd.DataFrame(columns=df_all.columns)
            df_subset.to_excel(writer, sheet_name=sheet_name, index=False)


def export_csv(store: JobStore, job_id: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flat_rows = _flat_rows(store, job_id)
    if not flat_rows:
        output_path.write_text("")
        return
    fieldnames = list(flat_rows[0].keys())
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)


def build_filtered_xlsx(store: JobStore, job_id: str, filter_: str | None, search: str | None) -> bytes:
    """A single-sheet workbook matching exactly the rows a filter/search
    combination shows in the Results table - not cached on disk, since the
    combination is query-specific rather than a reusable artifact."""
    rows = store.query_all_results(job_id, filter_, search)
    flat_rows = [_flatten(r) for r in rows]
    df = pd.DataFrame(flat_rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Validation Results", index=False)
    return buf.getvalue()


def build_filtered_csv(store: JobStore, job_id: str, filter_: str | None, search: str | None) -> bytes:
    rows = store.query_all_results(job_id, filter_, search)
    flat_rows = [_flatten(r) for r in rows]
    if not flat_rows:
        return b""
    buf = io.StringIO()
    fieldnames = list(flat_rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(flat_rows)
    return buf.getvalue().encode("utf-8")
