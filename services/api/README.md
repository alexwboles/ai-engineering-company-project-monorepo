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

### Incident manager

- `POST /api/incidents`
  - Creates a new incident record.
  - Returns `400` with field-specific validation details for invalid input.
- `GET /api/incidents`
  - Lists incidents.
  - Optional query params: `status`, `origin`, `branch`, `category`.
- `GET /api/incidents/{id}`
  - Returns one incident by identifier.
  - Returns `404` when no incident exists.
- `PATCH /api/incidents/{id}/status`
  - Updates only incident status using lifecycle rules.
  - Returns `400` for invalid transitions.
- `GET /api/incidents/summary`
  - Returns aggregate metrics totals by status, category, origin, and branch.

### Historical incident seed script

From repository root:

```bash
python scripts/seed_incidents.py
```

The seed script is idempotent and does not duplicate rows already loaded from the source CSV.

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

### Authentication and password flows

- `POST /auth/login`
  - Authenticates a user and returns a bearer JWT.
- `GET /auth/me`
  - Returns authenticated user and profile details.
- `POST /auth/forgot-password`
  - Body: `{ "email": "user@example.com" }`
  - Always returns `200` with a generic confirmation message.
  - If email exists, sends one-time password reset email.
- `POST /auth/reset-password`
  - Body: `{ "token": "...", "new_password": "..." }`
  - Validates signed reset token, expiry, and one-time token usage.
  - Returns `400` for invalid, expired, or already-used token.
- `POST /auth/change-password`
  - Authenticated endpoint.
  - Body: `{ "current_password": "...", "new_password": "..." }`
  - Returns `400` when current password does not match.

## Authentication env variables

Add the following values in `.env` based on `.env.example`:

- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `JWT_ALGORITHM`
- `RESET_TOKEN_EXPIRE_MINUTES`
- `RESET_TOKEN_SECRET_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `FRONTEND_RESET_PASSWORD_URL`

## Telemetry storage

Apply `supabase/migrations/20260803210000_create_telemetry_events.sql` to the
Supabase project before enabling production telemetry storage. The API reads
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and the optional
`SUPABASE_TELEMETRY_TABLE` setting. The telemetry endpoint validates events
individually, inserts valid rows as one PostgREST batch, and returns the
received, stored, and rejected counts. When Supabase settings are absent, the
local development process uses an in-memory store instead of sending data
outside the machine.

`FRONTEND_RESET_PASSWORD_URL` should point to the internal frontend reset route, for example:

- `http://localhost:3000/reset-password` (Backoffice local)
- `http://localhost:3001/reset-password` (Talent local)

## Error handling

- Empty upload: `400`
- Non-CSV extension: `400`
- Invalid encoding/format: `400`
- Export before any analysis: `404`
