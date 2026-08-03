from __future__ import annotations

import sys

try:
    from services.api.routes.suppliers import seed_suppliers
except ModuleNotFoundError:
    from routes.suppliers import seed_suppliers


def main() -> int:
    try:
        inserted = seed_suppliers()
    except Exception as exc:
        print(f"Seed failed: unable to insert suppliers ({type(exc).__name__}).", file=sys.stderr)
        return 1

    print(f"Seed complete. Inserted {inserted} supplier record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
