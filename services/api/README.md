# Incident Analysis API

## Setup

```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Endpoints

- `POST /api/incidents/analyze`
  - `multipart/form-data` with field name `file`
  - Returns summary JSON and invalid-record details.
- `GET /api/incidents/results/export`
  - Returns downloadable `results.csv` from the latest analysis.

## Error handling

- Empty upload: `400`
- Non-CSV extension: `400`
- Invalid encoding/format: `400`
- Export before any analysis: `404`
