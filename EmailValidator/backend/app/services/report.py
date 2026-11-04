from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.job_store import JobStore


def compute_summary(store: JobStore, job_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    total_uploaded = metadata.get("total_records", 0)
    unique_emails = 0
    duplicate_emails = 0
    valid_count = invalid_count = risky_count = unknown_count = 0
    disposable_count = free_provider_count = role_based_count = 0

    for row in store.iter_results(job_id):
        if row.get("is_duplicate"):
            duplicate_emails += 1
        else:
            unique_emails += 1

        status = row.get("final_status")
        if status == "valid":
            valid_count += 1
        elif status == "invalid":
            invalid_count += 1
        elif status == "risky":
            risky_count += 1
        elif status == "unknown":
            unknown_count += 1

        if row.get("disposable"):
            disposable_count += 1
        if row.get("free_provider"):
            free_provider_count += 1
        if row.get("role_based"):
            role_based_count += 1

    processed = valid_count + invalid_count + risky_count + unknown_count
    success_percent = round((valid_count / processed * 100), 2) if processed else 0.0

    started_at = metadata.get("started_at")
    completed_at = metadata.get("completed_at")
    duration = None
    if started_at and completed_at:
        try:
            duration = (datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)).total_seconds()
        except ValueError:
            duration = None

    return {
        "job_id": job_id,
        "total_uploaded": total_uploaded,
        "unique_emails": unique_emails,
        "duplicate_emails": duplicate_emails,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "risky_count": risky_count,
        "unknown_count": unknown_count,
        "disposable_count": disposable_count,
        "free_provider_count": free_provider_count,
        "role_based_count": role_based_count,
        "success_percent": success_percent,
        "validation_duration_seconds": duration,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def generate_pdf_report(summary: dict[str, Any], metadata: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Bulk Email Validation Report", styles["Title"]))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(f"Source file: {metadata.get('original_filename', 'n/a')}", styles["Normal"]))
    elements.append(Paragraph(f"Job ID: {summary['job_id']}", styles["Normal"]))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    table_data = [
        ["Metric", "Value"],
        ["Total emails uploaded", summary["total_uploaded"]],
        ["Unique email addresses", summary["unique_emails"]],
        ["Duplicate email addresses", summary["duplicate_emails"]],
        ["Valid emails", summary["valid_count"]],
        ["Invalid emails", summary["invalid_count"]],
        ["Risky emails", summary["risky_count"]],
        ["Unknown emails", summary["unknown_count"]],
        ["Disposable emails", summary["disposable_count"]],
        ["Free provider emails", summary["free_provider_count"]],
        ["Role-based emails", summary["role_based_count"]],
        ["Success percentage", f"{summary['success_percent']}%"],
        ["Validation duration (s)", summary.get("validation_duration_seconds") or "n/a"],
    ]
    table = Table(table_data, colWidths=[8 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 1 * cm))

    distribution = [
        ("Valid", summary["valid_count"], colors.HexColor("#2E7D32")),
        ("Invalid", summary["invalid_count"], colors.HexColor("#C62828")),
        ("Risky", summary["risky_count"], colors.HexColor("#F9A825")),
        ("Unknown", summary["unknown_count"], colors.HexColor("#616161")),
    ]
    nonzero = [d for d in distribution if d[1] > 0]
    if nonzero:
        elements.append(Paragraph("Validation Distribution", styles["Heading2"]))
        drawing = Drawing(400, 220)
        pie = Pie()
        pie.x, pie.y, pie.width, pie.height = 100, 20, 160, 160
        pie.data = [d[1] for d in nonzero]
        pie.labels = [f"{d[0]} ({d[1]})" for d in nonzero]
        pie.slices.strokeWidth = 0.5
        for i, (_, _, color) in enumerate(nonzero):
            pie.slices[i].fillColor = color
        drawing.add(pie)
        elements.append(drawing)

    doc.build(elements)
