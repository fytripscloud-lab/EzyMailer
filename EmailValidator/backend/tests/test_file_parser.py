import pandas as pd
import pytest

from app.services.file_parser import (
    content_matches_extension,
    detect_email_column,
    extract_email_records,
    sniff_container_kind,
)


def test_detect_email_column_by_header_alias():
    df = pd.DataFrame({"Name": ["A"], "Email Address": ["a@example.com"]})
    assert detect_email_column(df) == "Email Address"


def test_detect_email_column_by_content_sniffing():
    df = pd.DataFrame({"Name": ["A", "B"], "Contact": ["a@example.com", "b@example.com"]})
    assert detect_email_column(df) == "Contact"


def test_detect_email_column_none_found():
    df = pd.DataFrame({"Name": ["A"], "Age": ["30"]})
    assert detect_email_column(df) is None


def test_extract_email_records_preserves_rows_and_marks_duplicates():
    df = pd.DataFrame(
        {
            "Name": ["A", "B", "C", "D"],
            "Email": ["a@example.com", "", "a@example.com", "bad-email"],
        }
    )
    records = extract_email_records(df, "Email")
    assert len(records) == 4
    assert records[0]["row_no"] == 2  # header is row 1
    assert records[1]["email"] == ""
    assert records[1]["is_duplicate"] is False
    assert records[2]["email"] == "a@example.com"
    assert records[2]["is_duplicate"] is True
    assert records[3]["email"] == "bad-email"
    assert records[0]["original"]["Name"] == "A"


def test_sniff_container_kind_csv():
    assert sniff_container_kind(b"name,email\nA,a@example.com\n") == "csv"


def test_sniff_container_kind_xlsx():
    assert sniff_container_kind(b"PK\x03\x04rest-of-zip") == "xlsx"


def test_sniff_container_kind_xls():
    assert sniff_container_kind(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest") == "xls"


def test_sniff_container_kind_unknown_binary():
    assert sniff_container_kind(bytes(range(200, 256))) is None


@pytest.mark.parametrize(
    "extension,content,expected",
    [
        (".csv", b"a,b\n1,2\n", True),
        (".xlsx", b"PK\x03\x04zip", True),
        (".xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1ole", True),
        (".xlsx", b"a,b\n1,2\n", False),
        (".csv", b"PK\x03\x04zip", False),
    ],
)
def test_content_matches_extension(extension, content, expected):
    assert content_matches_extension(extension, content) is expected
