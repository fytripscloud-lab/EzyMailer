import pandas as pd

from app.services import exporter, report
from app.services.job_store import JobStore


def _seed_job(store: JobStore, job_id: str):
    store.init_job(
        job_id,
        {
            "status": "completed",
            "total_records": 3,
            "original_filename": "list.csv",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:05+00:00",
        },
    )
    store.truncate_results(job_id)
    rows = [
        {
            "row_no": 2, "original": {"Name": "A"}, "email": "a@example.com",
            "syntax_valid": True, "domain_valid": True, "mx_found": True, "smtp": "accepted",
            "disposable": False, "free_provider": True, "role_based": False,
            "catch_all": "no", "final_status": "valid", "is_duplicate": False,
        },
        {
            "row_no": 3, "original": {"Name": "B"}, "email": "bad-email",
            "syntax_valid": False, "domain_valid": False, "mx_found": False, "smtp": "unknown",
            "disposable": False, "free_provider": False, "role_based": False,
            "catch_all": "unknown", "final_status": "invalid", "is_duplicate": False,
        },
        {
            "row_no": 4, "original": {"Name": "C"}, "email": "admin@mailinator.com",
            "syntax_valid": True, "domain_valid": True, "mx_found": True, "smtp": "unknown",
            "disposable": True, "free_provider": False, "role_based": True,
            "catch_all": "unknown", "final_status": "risky", "is_duplicate": False,
        },
    ]
    for r in rows:
        store.append_result(job_id, r)
    return rows


def test_compute_summary(test_settings):
    store = JobStore(test_settings)
    job_id = "1" * 32
    _seed_job(store, job_id)
    metadata = store.load_metadata(job_id)

    summary = report.compute_summary(store, job_id, metadata)

    assert summary["total_uploaded"] == 3
    assert summary["valid_count"] == 1
    assert summary["invalid_count"] == 1
    assert summary["risky_count"] == 1
    assert summary["unknown_count"] == 0
    assert summary["disposable_count"] == 1
    assert summary["role_based_count"] == 1
    assert summary["validation_duration_seconds"] == 5.0

    store.delete_job(job_id)


def test_export_xlsx_contains_expected_sheets(test_settings, tmp_path):
    store = JobStore(test_settings)
    job_id = "2" * 32
    _seed_job(store, job_id)

    out_path = tmp_path / "out.xlsx"
    exporter.export_xlsx(store, job_id, out_path)

    assert out_path.exists()
    sheets = pd.read_excel(out_path, sheet_name=None)
    assert set(sheets.keys()) == {"All Results", "Valid Emails", "Invalid Emails", "Risky Emails", "Unknown Emails"}
    assert len(sheets["All Results"]) == 3
    assert len(sheets["Valid Emails"]) == 1
    assert len(sheets["Invalid Emails"]) == 1
    assert len(sheets["Risky Emails"]) == 1
    assert len(sheets["Unknown Emails"]) == 0
    # Original columns preserved alongside validation columns
    assert "Name" in sheets["All Results"].columns
    assert "Final Status" in sheets["All Results"].columns

    store.delete_job(job_id)


def test_export_csv(test_settings, tmp_path):
    store = JobStore(test_settings)
    job_id = "3" * 32
    _seed_job(store, job_id)

    out_path = tmp_path / "out.csv"
    exporter.export_csv(store, job_id, out_path)

    content = out_path.read_text()
    assert "a@example.com" in content
    assert "Final Status" in content

    store.delete_job(job_id)


def test_generate_pdf_report(test_settings, tmp_path):
    store = JobStore(test_settings)
    job_id = "4" * 32
    _seed_job(store, job_id)
    metadata = store.load_metadata(job_id)
    summary = report.compute_summary(store, job_id, metadata)

    out_path = tmp_path / "report.pdf"
    report.generate_pdf_report(summary, metadata, out_path)

    assert out_path.exists()
    assert out_path.read_bytes().startswith(b"%PDF")

    store.delete_job(job_id)


def test_build_filtered_xlsx_matches_table_filter(test_settings):
    store = JobStore(test_settings)
    job_id = "5" * 32
    _seed_job(store, job_id)

    content = exporter.build_filtered_xlsx(store, job_id, "risky", None)
    assert content.startswith(b"PK")

    import io

    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)
    assert set(sheets.keys()) == {"Validation Results"}
    df = sheets["Validation Results"]
    assert len(df) == 1
    assert df.iloc[0]["Email"] == "admin@mailinator.com"

    store.delete_job(job_id)


def test_build_filtered_xlsx_matches_search(test_settings):
    store = JobStore(test_settings)
    job_id = "6" * 32
    _seed_job(store, job_id)

    content = exporter.build_filtered_xlsx(store, job_id, "all", "mailinator")

    import io

    df = pd.read_excel(io.BytesIO(content), sheet_name="Validation Results")
    assert len(df) == 1
    assert df.iloc[0]["Email"] == "admin@mailinator.com"

    store.delete_job(job_id)


def test_build_filtered_csv_matches_table_filter(test_settings):
    store = JobStore(test_settings)
    job_id = "7" * 32
    _seed_job(store, job_id)

    content = exporter.build_filtered_csv(store, job_id, "valid", None)
    text = content.decode("utf-8")
    assert "a@example.com" in text
    assert "admin@mailinator.com" not in text
    assert "bad-email" not in text

    store.delete_job(job_id)


def test_build_filtered_csv_empty_result(test_settings):
    store = JobStore(test_settings)
    job_id = "8" * 32
    _seed_job(store, job_id)

    content = exporter.build_filtered_csv(store, job_id, "all", "no-such-email")
    assert content == b""

    store.delete_job(job_id)
