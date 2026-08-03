from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Allow importing the shared analysis module from services/api.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.incident_analysis import load_and_analyze_csv, summary_to_csv_text, summary_to_dict
from services.api.incident_analysis.config import DEFAULT_EXPECTED_RESULTS_PATH


def format_summary(summary: dict[str, object], invalid_preview: list[dict[str, object]]) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("INCIDENT ANALYSIS SUMMARY")
    lines.append("=" * 78)
    lines.append(f"Total records processed : {summary['total_records']}")
    lines.append(f"Valid records           : {summary['valid_records']}")
    lines.append(f"Invalid records         : {summary['invalid_records']}")
    lines.append("-" * 78)
    lines.append("Breakdown by category (valid records)")
    category_breakdown = summary.get("category_breakdown", {})
    for category, count in sorted(category_breakdown.items()):
        lines.append(f"  - {category:<22} {count}")
    lines.append("-" * 78)
    lines.append("Breakdown by status (valid records)")
    status_breakdown = summary.get("status_breakdown", {})
    for status, count in sorted(status_breakdown.items()):
        lines.append(f"  - {status:<22} {count}")
    lines.append("-" * 78)
    lines.append("Invalid records by reason")
    invalid_by_reason = summary.get("invalid_by_reason", {})
    for reason, count in sorted(invalid_by_reason.items()):
        lines.append(f"  - {reason:<22} {count}")
    lines.append("-" * 78)
    avg = summary.get("average_satisfaction_closed")
    if avg is None:
        lines.append("Average satisfaction (closed with score): N/A")
    else:
        lines.append(f"Average satisfaction (closed with score): {float(avg):.4f}")

    if invalid_preview:
        lines.append("-" * 78)
        lines.append("Invalid record preview (first 10 issues)")
        for issue in invalid_preview[:10]:
            lines.append(
                f"  - row={issue['row_number']}, incident={issue['incident_id']}, "
                f"reason={issue['reason']}, details={issue['details']}"
            )

    lines.append("=" * 78)
    return "\n".join(lines)


def verify_against_expected(summary: dict[str, object], expected_path: Path) -> int:
    if not expected_path.exists():
        print(f"Expected-values file not found at {expected_path.name}. Verification skipped.", file=sys.stderr)
        return 0

    try:
        with expected_path.open("r", encoding="utf-8") as handle:
            expected = json.load(handle)
    except OSError as exc:
        print(f"Error: Unable to read expected values file ({exc.strerror}).", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("Error: Expected values file is not valid JSON.", file=sys.stderr)
        return 1

    mismatches: list[str] = []
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            mismatches.append(f"{key}: expected={expected_value!r}, actual={summary.get(key)!r}")

    if mismatches:
        print("Verification result: FAILED", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  - {mismatch}", file=sys.stderr)
        return 1

    print("Verification result: OK (matches expected values)")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <path-to-incidents-csv>", file=sys.stderr)
        return 1

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path.name}", file=sys.stderr)
        return 1

    try:
        summary, invalid_records, _valid_rows = load_and_analyze_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path.name}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print("Error: CSV must be UTF-8 encoded.", file=sys.stderr)
        return 1
    except (csv.Error, ValueError) as exc:
        print(f"Error: Unable to parse CSV ({exc}).", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: Unable to read CSV ({exc.strerror}).", file=sys.stderr)
        return 1
    except Exception:
        print("Error: Unexpected failure while analyzing the CSV.", file=sys.stderr)
        return 1

    summary_dict = summary_to_dict(summary)
    invalid_preview = [
        {
            "row_number": issue.row_number,
            "incident_id": issue.incident_id,
            "reason": issue.reason,
            "details": issue.details,
        }
        for issue in invalid_records
    ]

    print(format_summary(summary_dict, invalid_preview))
    verification_status = verify_against_expected(summary_dict, DEFAULT_EXPECTED_RESULTS_PATH)

    try:
        choice = input("Export results to CSV? [y / n]: ").strip().lower()
    except EOFError:
        choice = "n"

    if choice == "y":
        output_path = ROOT / "scripts" / "results.csv"
        try:
            output_path.write_text(summary_to_csv_text(summary), encoding="utf-8")
        except OSError as exc:
            print(f"Error: Unable to write results CSV ({exc.strerror}).", file=sys.stderr)
            return 1
        print(f"Results saved to {output_path.name}")
    else:
        print("Export skipped.")

    return verification_status


if __name__ == "__main__":
    raise SystemExit(main())
