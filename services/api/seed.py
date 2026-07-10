from __future__ import annotations

try:
    from services.api.routes.suppliers import seed_suppliers
except ModuleNotFoundError:
    from routes.suppliers import seed_suppliers


def main() -> None:
    inserted = seed_suppliers()
    print(f"Seed complete. Inserted {inserted} supplier record(s).")


if __name__ == "__main__":
    main()
