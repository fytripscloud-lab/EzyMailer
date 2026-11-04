import time

import dns.resolver
import pytest

from app.config import get_settings
from app.services.checks import smtp_check as smtp_check_module
from tests.conftest import make_csv_bytes


class FakeMx:
    def __init__(self, exchange):
        self.preference = 10
        self.exchange = exchange + "."


class FakeSMTP:
    """250 for any real-looking recipient, 550 for the random catch-all
    probe addresses (local part prefixed by SmtpChecker.check_catch_all)."""

    def __init__(self, hostname=None, port=None, timeout=None, start_tls=None):
        pass

    async def connect(self):
        pass

    async def ehlo(self, hostname=None):
        pass

    async def mail(self, sender):
        pass

    async def rcpt(self, recipient):
        local = recipient.split("@")[0]
        if local.startswith("nonexistent-"):
            return (550, "No such user")
        return (250, "OK")

    async def quit(self):
        pass


@pytest.fixture
def test_settings(tmp_imported_dir, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("IMPORTED_DIR", str(tmp_imported_dir))
    monkeypatch.setenv("ENABLE_SMTP_CHECK", "true")
    monkeypatch.setenv("ENABLE_CATCH_ALL_CHECK", "true")
    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.processing_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    yield settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def fake_network(monkeypatch):
    def fake_resolve(self, qname, rtype):
        if rtype == "MX":
            if qname in ("example.com", "mailinator.com"):
                return [FakeMx(f"mx.{qname}")]
            raise dns.resolver.NXDOMAIN()
        if rtype == "A":
            if qname.startswith("mx."):
                return ["93.184.216.34"]
            raise dns.resolver.NXDOMAIN()
        raise dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)
    monkeypatch.setattr(smtp_check_module.aiosmtplib, "SMTP", FakeSMTP)


def _wait_for_completion(client, job_id, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/api/v1/bulk-validator/progress/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] in ("completed", "cancelled", "failed"):
            return data
        time.sleep(0.05)
    raise AssertionError("job did not complete in time")


def test_full_upload_to_export_flow(client):
    content = make_csv_bytes(
        [
            {"Name": "Alice", "Email": "alice@example.com"},
            {"Name": "Bob", "Email": "bob@nowhere-invalid-domain.invalid"},
            {"Name": "Spammer", "Email": "admin@mailinator.com"},
            {"Name": "Dup", "Email": "alice@example.com"},
            {"Name": "Blank", "Email": ""},
        ]
    )
    upload_resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200
    job_id = upload_resp.json()["job_id"]

    start_resp = client.post(f"/api/v1/bulk-validator/start/{job_id}")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "validating"

    progress = _wait_for_completion(client, job_id)
    assert progress["status"] == "completed"
    assert progress["processed"] == 5

    results_resp = client.get(f"/api/v1/bulk-validator/results/{job_id}")
    assert results_resp.status_code == 200
    assert results_resp.json()["total_rows"] == 5

    # alice@example.com appears twice (original + duplicate), both valid
    assert client.get(f"/api/v1/bulk-validator/results/{job_id}", params={"filter": "valid"}).json()["total_rows"] == 2
    # bob's invalid domain + the blank row (bad syntax)
    assert client.get(f"/api/v1/bulk-validator/results/{job_id}", params={"filter": "invalid"}).json()["total_rows"] == 2
    # admin@mailinator.com: disposable + role-based
    assert client.get(f"/api/v1/bulk-validator/results/{job_id}", params={"filter": "risky"}).json()["total_rows"] == 1
    assert client.get(f"/api/v1/bulk-validator/results/{job_id}", params={"filter": "disposable"}).json()["total_rows"] == 1
    assert client.get(f"/api/v1/bulk-validator/results/{job_id}", params={"search": "alice"}).json()["total_rows"] == 2

    report_resp = client.get(f"/api/v1/bulk-validator/report/{job_id}")
    assert report_resp.status_code == 200
    summary = report_resp.json()
    assert summary["total_uploaded"] == 5
    assert summary["duplicate_emails"] == 1
    assert summary["unique_emails"] == 4
    assert summary["valid_count"] == 2
    assert summary["risky_count"] == 1
    assert summary["disposable_count"] == 1

    for fmt, expected_prefix in [("xlsx", b"PK"), ("csv", None), ("pdf", b"%PDF")]:
        export_resp = client.get(f"/api/v1/bulk-validator/export/{job_id}", params={"format": fmt})
        assert export_resp.status_code == 200, export_resp.text
        if expected_prefix:
            assert export_resp.content.startswith(expected_prefix)

    # A filtered export ("Validation Results") matches exactly what the
    # table is currently showing, as a single sheet - not the full workbook.
    filtered_xlsx = client.get(
        f"/api/v1/bulk-validator/export/{job_id}", params={"format": "xlsx", "filter": "risky"}
    )
    assert filtered_xlsx.status_code == 200
    assert filtered_xlsx.content.startswith(b"PK")
    assert "validation_results_filtered.xlsx" in filtered_xlsx.headers["content-disposition"]
    import io

    import pandas as pd

    sheets = pd.read_excel(io.BytesIO(filtered_xlsx.content), sheet_name=None)
    assert set(sheets.keys()) == {"Validation Results"}
    assert len(sheets["Validation Results"]) == 1  # only the mailinator.com row

    filtered_csv = client.get(
        f"/api/v1/bulk-validator/export/{job_id}", params={"format": "csv", "search": "alice"}
    )
    assert filtered_csv.status_code == 200
    assert "validation_results_filtered.csv" in filtered_csv.headers["content-disposition"]
    csv_text = filtered_csv.content.decode("utf-8")
    assert csv_text.count("alice@example.com") == 2  # original + duplicate row
    assert "not-an-email" not in csv_text

    # format=all with no search still serves the cached full multi-sheet workbook.
    full_xlsx = client.get(f"/api/v1/bulk-validator/export/{job_id}", params={"format": "xlsx", "filter": "all"})
    assert "validation_results.xlsx" in full_xlsx.headers["content-disposition"]

    delete_resp = client.delete(f"/api/v1/bulk-validator/job/{job_id}")
    assert delete_resp.status_code == 200

    after_delete = client.get(f"/api/v1/bulk-validator/progress/{job_id}")
    assert after_delete.status_code == 404


def test_start_with_manual_column_selection(client):
    # Only 1/3 of "Contact" values look like an email, below the 50% content-
    # sniffing auto-detect threshold, so this requires manual column selection.
    content = make_csv_bytes(
        [
            {"Name": "Alice", "Contact": "alice@example.com"},
            {"Name": "Bob", "Contact": "not-an-email"},
            {"Name": "Carol", "Contact": "xyz"},
        ]
    )
    upload_resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    job_id = upload_resp.json()["job_id"]
    assert upload_resp.json()["requires_column_selection"] is True

    start_resp = client.post(
        f"/api/v1/bulk-validator/start/{job_id}",
        json={"email_column": "Contact"},
    )
    assert start_resp.status_code == 200
    _wait_for_completion(client, job_id)

    results = client.get(f"/api/v1/bulk-validator/results/{job_id}").json()
    assert results["rows"][0]["email"] == "alice@example.com"

    client.delete(f"/api/v1/bulk-validator/job/{job_id}")


def test_start_without_valid_column_fails(client):
    content = make_csv_bytes([{"Name": "Alice", "Phone": "123"}])
    upload_resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    job_id = upload_resp.json()["job_id"]

    start_resp = client.post(f"/api/v1/bulk-validator/start/{job_id}")
    assert start_resp.status_code == 400

    client.delete(f"/api/v1/bulk-validator/job/{job_id}")


def test_cancel_job(client):
    rows = [{"Name": f"N{i}", "Email": f"user{i}@example.com"} for i in range(50)]
    content = make_csv_bytes(rows)
    upload_resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    job_id = upload_resp.json()["job_id"]

    client.post(f"/api/v1/bulk-validator/start/{job_id}")
    cancel_resp = client.post(f"/api/v1/bulk-validator/cancel/{job_id}")
    assert cancel_resp.status_code in (200, 409)  # 409 if it already finished before we could cancel

    final = _wait_for_completion(client, job_id)
    assert final["status"] in ("completed", "cancelled")

    client.delete(f"/api/v1/bulk-validator/job/{job_id}")


def test_report_before_completion_returns_409(client):
    content = make_csv_bytes([{"Name": "Alice", "Email": "alice@example.com"}])
    upload_resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    job_id = upload_resp.json()["job_id"]

    report_resp = client.get(f"/api/v1/bulk-validator/report/{job_id}")
    assert report_resp.status_code == 409

    client.delete(f"/api/v1/bulk-validator/job/{job_id}")
