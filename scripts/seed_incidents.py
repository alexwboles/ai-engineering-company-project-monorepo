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


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_path)

    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)

    inserted_count = 0
    skipped_count = 0
    invalid_rows: list[dict[str, object]] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        if reader.fieldnames is None:
            print("CSV is missing a header row.")
            sys.exit(1)

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
            _, inserted = IncidentsService.upsert_seed_incident(cleaned, source_incident_id)
            if inserted:
                inserted_count += 1
            else:
                skipped_count += 1

    print("Incident seed complete.")
    print(f"Inserted: {inserted_count}")
    print(f"Skipped (already present): {skipped_count}")
    print(f"Invalid rows: {len(invalid_rows)}")

    if invalid_rows:
        print("\nInvalid row details:")
        for issue in invalid_rows:
            row = issue["row"]
            incident_id = issue["incident_id"]
            print(f"- row={row}, incident_id={incident_id}")
            for error in issue["errors"]:
                print(f"    field={error['field']} message={error['message']}")


if __name__ == "__main__":
    main()
