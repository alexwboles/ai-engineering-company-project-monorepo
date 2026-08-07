from __future__ import annotations

import csv
import io
from typing import Any

from .models import AnalysisSummary


def summary_to_csv_text(summary: AnalysisSummary) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["metric", "value"])
    writer.writerow(["total_records", summary.total_records])
    writer.writerow(["valid_records", summary.valid_records])
    writer.writerow(["invalid_records", summary.invalid_records])

    for reason, count in sorted(summary.invalid_by_reason.items()):
        writer.writerow([f"invalid_reason.{reason}", count])

    for category, count in sorted(summary.category_breakdown.items()):
        writer.writerow([f"category.{category}", count])

    for status, count in sorted(summary.status_breakdown.items()):
        writer.writerow([f"status.{status}", count])

    for clinic, count in sorted(summary.clinic_breakdown.items()):
        writer.writerow([f"clinic.{clinic}", count])

    for country, count in sorted(summary.country_breakdown.items()):
        writer.writerow([f"country.{country}", count])

    avg_value: Any = ""
    if summary.average_satisfaction_closed is not None:
        avg_value = f"{summary.average_satisfaction_closed:.4f}"
    writer.writerow(["average_satisfaction_closed", avg_value])

    return stream.getvalue()
