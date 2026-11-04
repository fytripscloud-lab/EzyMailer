import re
from pathlib import Path
from typing import Any

import pandas as pd

EMAIL_HEADER_ALIASES = {
    "email", "emails", "email address", "email addresses", "e-mail", "e mail",
    "mail", "contact email", "emailid", "email id", "e-mail address",
    "primary email", "work email", "business email",
}

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UnsupportedFileError(ValueError):
    pass


def sniff_container_kind(content: bytes) -> str | None:
    """Magic-byte sniff of the actual bytes, independent of the claimed
    extension, to stop disguised/unsafe uploads."""
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    try:
        content[:8192].decode("utf-8")
        return "csv"
    except UnicodeDecodeError:
        return None


def content_matches_extension(extension: str, content: bytes) -> bool:
    kind = sniff_container_kind(content)
    extension = extension.lower().lstrip(".")
    if kind is None:
        return False
    if extension == "xlsx":
        return kind == "xlsx"
    if extension == "xls":
        return kind in ("xls", "xlsx")
    if extension == "csv":
        return kind == "csv"
    return False


def list_sheets(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        return ["Sheet1"]
    try:
        xls = pd.ExcelFile(path)
    except Exception as exc:
        raise UnsupportedFileError(f"could not read workbook: {exc}") from exc
    return xls.sheet_names


def read_sheet(path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        elif suffix == ".xlsx":
            df = pd.read_excel(path, sheet_name=sheet_name or 0, dtype=str, keep_default_na=False, engine="openpyxl")
        elif suffix == ".xls":
            df = pd.read_excel(path, sheet_name=sheet_name or 0, dtype=str, keep_default_na=False, engine="xlrd")
        else:
            raise UnsupportedFileError(f"unsupported extension: {suffix}")
    except UnsupportedFileError:
        raise
    except Exception as exc:
        raise UnsupportedFileError(f"could not parse file: {exc}") from exc

    df.columns = [str(c).strip() for c in df.columns]
    # Drop fully-blank rows (every cell empty) but keep partially blank ones
    # so we never silently discard rows that simply have no email value.
    df = df[~(df.astype(str).apply(lambda r: r.str.strip().eq("").all(), axis=1))]
    df = df.reset_index(drop=True)
    return df


def detect_email_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if col.strip().lower() in EMAIL_HEADER_ALIASES:
            return col

    for col in df.columns:
        lc = col.strip().lower()
        if "email" in lc or "e-mail" in lc or lc == "mail" or lc.endswith(" mail"):
            return col

    best_col: str | None = None
    best_ratio = 0.0
    for col in df.columns:
        sample = df[col].astype(str).head(50)
        if len(sample) == 0:
            continue
        matches = sum(1 for v in sample if EMAIL_REGEX.match(v.strip()))
        ratio = matches / len(sample)
        if ratio > best_ratio and ratio >= 0.5:
            best_ratio = ratio
            best_col = col
    return best_col


def extract_email_records(df: pd.DataFrame, email_column: str) -> list[dict[str, Any]]:
    """row_no is the 1-based spreadsheet row number (header counted as row 1)."""
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, row in df.iterrows():
        row_no = int(idx) + 2
        raw_email = str(row.get(email_column, "") or "").strip()
        original = {k: ("" if v is None else str(v)) for k, v in row.to_dict().items()}
        is_duplicate = False
        if raw_email:
            key = raw_email.lower()
            if key in seen:
                is_duplicate = True
            else:
                seen.add(key)
        records.append(
            {
                "row_no": row_no,
                "email": raw_email,
                "original": original,
                "is_duplicate": is_duplicate,
            }
        )
    return records
