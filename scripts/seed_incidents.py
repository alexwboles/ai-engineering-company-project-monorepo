from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.shared.incident_manager_validation import (
    transform_csv_row_to_incident_seed,
    validate_historical_csv_row,
    validate_incident_payload,
)
from services.api.incidents_service import IncidentsService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed incident manager data from historical CSV records.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(ROOT / "scripts" / "incidents-COMPANY.csv"),
        help="Path to the historical incidents CSV file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv_path)

    if not csv_path.exists():
        print(f"CSV file not found: {csv_path.name}", file=sys.stderr)
        return 1

    inserted_count = 0
    skipped_count = 0
    invalid_rows: list[dict[str, object]] = []

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            if reader.fieldnames is None:
                print("CSV is missing a header row.", file=sys.stderr)
                return 1

            for row_number, row in enumerate(reader, start=2):
                historical_errors = validate_historical_csv_row(row)
                if historical_errors:
                    invalid_rows.append(
                        {
                            "row": row_number,
                            "incident_id": (row.get("incident_id") or "<missing>"),
                            "errors": historical_errors,
                        }
                    )
                    continue

                transformed, source_incident_id, transform_errors = transform_csv_row_to_incident_seed(row)
                if transform_errors:
                    invalid_rows.append(
                        {
                            "row": row_number,
                            "incident_id": source_incident_id or "<missing>",
                            "errors": transform_errors,
                        }
                    )
                    continue

                cleaned, validation_errors = validate_incident_payload(transformed)
                if validation_errors:
                    invalid_rows.append(
                        {
                            "row": row_number,
                            "incident_id": source_incident_id,
                            "errors": validation_errors,
                        }
                    )
                    continue

                cleaned["created_at"] = transformed["created_at"]
                try:
                    _, inserted = IncidentsService.upsert_seed_incident(cleaned, source_incident_id)
                except Exception as exc:
                    print(
                        f"Error seeding row {row_number}: unable to write incident data ({type(exc).__name__}).",
                        file=sys.stderr,
                    )
                    return 1

                if inserted:
                    inserted_count += 1
                else:
                    skipped_count += 1
    except UnicodeDecodeError:
        print("Error: CSV must be UTF-8 encoded.", file=sys.stderr)
        return 1
    except csv.Error as exc:
        print(f"Error: Unable to parse CSV ({exc}).", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: Unable to read CSV ({exc.strerror}).", file=sys.stderr)
        return 1

    print("Incident seed complete.")
    print(f"Inserted: {inserted_count}")
    print(f"Skipped (already present): {skipped_count}")
    print(f"Invalid rows: {len(invalid_rows)}")

    if invalid_rows:
        print("\nInvalid row details:", file=sys.stderr)
        for issue in invalid_rows:
            row = issue["row"]
            incident_id = issue["incident_id"]
            print(f"- row={row}, incident_id={incident_id}", file=sys.stderr)
            for error in issue["errors"]:
                print(f"    field={error['field']} message={error['message']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
