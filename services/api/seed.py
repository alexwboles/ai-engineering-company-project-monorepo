from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
