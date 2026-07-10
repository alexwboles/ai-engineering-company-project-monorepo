# Incident Analysis API

## Setup

```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Seed suppliers (idempotent)
uv run seed
```

## Supplier Backend Structure

The supplier directory follows this layout:

- `main.py` - FastAPI application
- `models.py` - Pydantic supplier models
- `database.py` - TinyDB initialization
- `routes/suppliers.py` - Supplier directory endpoints
- `seed.py` - Initial supplier data loading script

## Endpoints

- `POST /api/incidents/analyze`
  - `multipart/form-data` with field name `file`
  - Returns summary JSON and invalid-record details.
- `GET /api/incidents/results/export`
  - Returns downloadable `results.csv` from the latest analysis.

### Supplier directory

- `POST /suppliers`
  - Creates a supplier and returns it with TinyDB `id`.
  - Invalid payloads return `422`.
- `GET /suppliers`
  - Lists all suppliers.
  - Optional query params: `country`, `category`.
- `GET /suppliers/{id}`
  - Returns supplier by ID.
  - Returns `404` when not found.
- `PATCH /suppliers/{id}/rate`
  - Updates supplier `rate` and auto-updates `last_rate_update_date` and `updated_at`.
  - Rejects `rate <= 0` with `422`.
- `PATCH /suppliers/{id}/status`
  - Updates supplier status.
  - Allowed values: `active`, `suspended`.
  - Invalid values return `422`.
- `DELETE /suppliers/{id}`
  - Removes supplier by ID.
  - Returns `404` when not found.

## Error handling

- Empty upload: `400`
- Non-CSV extension: `400`
- Invalid encoding/format: `400`
- Export before any analysis: `404`
