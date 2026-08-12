# Supplier Directory

This implementation follows the supplier assignment context represented in this repository by [`CONTEXT.md`](../CONTEXT.md) and [`CONTEXT_HEALTHCORE.md`](../CONTEXT_HEALTHCORE.md). The supplier-specific contract is implemented in `services/api/models.py` and uses the HealthCore supplier directory fields: `name`, `country`, `categories`, `monthly_rate`, `currency`, `updated_at`, `status`, `compliance_agreement`, `contract_renewal_date`, `contact_email`, and `notes`.

## Run the API and seed the directory

```powershell
cd services/api
uv run seed
uvicorn main:app --reload --port 8000
```

The seeder loads the 15 suppliers defined by the HealthCore context and is idempotent. The command reports the inserted record count; a second run reports zero new records.

## Supplier endpoints

- `POST /suppliers` creates a supplier and returns the TinyDB ID.
- `GET /suppliers` lists all suppliers; `country` and `category` are optional filters.
- `GET /suppliers/{id}` returns one supplier or `404`.
- `PATCH /suppliers/{id}/rate` accepts a positive `monthly_rate` and records `updated_at`.
- `PATCH /suppliers/{id}/status` accepts only `active` or `suspended`.
- `DELETE /suppliers/{id}` removes a supplier or returns `404`.

Invalid status, country/currency combinations, categories, dates, emails, or non-positive monthly rates return `422` before TinyDB is changed.

The backoffice page is available at `/suppliers`. It loads the directory from the API, applies country/category filters without a page reload, supports registration and inline monthly-rate/status changes, displays compliance and audit fields, and uses distinct styles for active and suspended suppliers.

## Submission evidence

- [Seeder output](../screenshots/seed-output-terminal.png)
- [Filtered endpoint response](../screenshots/filter-endpoint-response.png)
- [Filtered supplier UI](../screenshots/supplier-list-filtered-ui.png)

Supplier behavior is covered by `services/api/tests/test_supplier_directory.py`, including successful creation, validation failures, filters, not-found responses, status changes, deletion, rate timestamp updates, and idempotent seeding.
