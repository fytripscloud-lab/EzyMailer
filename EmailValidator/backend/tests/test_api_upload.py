import io

from tests.conftest import make_csv_bytes


def test_upload_csv_success(client):
    content = make_csv_bytes(
        [
            {"Name": "Alice", "Email": "alice@example.com"},
            {"Name": "Bob", "Email": "bob@example.com"},
        ]
    )
    resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_records"] == 2
    assert data["detected_email_column"] == "Email"
    assert data["requires_column_selection"] is False
    assert len(data["job_id"]) == 32


def test_upload_rejects_disallowed_extension(client):
    resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.txt", b"name,email\na,a@example.com\n", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_rejects_content_extension_mismatch(client):
    # Claims .xlsx but is actually plain CSV bytes.
    resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.xlsx", b"name,email\na,a@example.com\n", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_upload_rejects_empty_file(client):
    resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400


def test_upload_missing_email_column_requires_manual_selection(client):
    content = make_csv_bytes([{"Name": "Alice", "Phone": "123"}])
    resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.csv", content, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected_email_column"] is None
    assert data["requires_column_selection"] is True
    assert "Name" in data["available_columns"]


def test_upload_detects_various_column_aliases(client):
    for header in ["E-mail", "Contact Email", "email address"]:
        content = make_csv_bytes([{header: "a@example.com", "Other": "x"}])
        resp = client.post(
            "/api/v1/bulk-validator/upload",
            files={"file": ("contacts.csv", content, "text/csv")},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detected_email_column"] == header


def test_upload_xlsx_success(client):
    import pandas as pd

    buf = io.BytesIO()
    df = pd.DataFrame({"Full Name": ["A", "B"], "Email": ["a@example.com", "b@example.com"]})
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)

    resp = client.post(
        "/api/v1/bulk-validator/upload",
        files={"file": ("contacts.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["detected_email_column"] == "Email"


def test_get_results_for_unknown_job_returns_404(client):
    resp = client.get("/api/v1/bulk-validator/results/" + "0" * 32)
    assert resp.status_code == 404
