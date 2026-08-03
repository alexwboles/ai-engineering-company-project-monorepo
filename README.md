# HealthCore Data Utilities (Milestone 2)

A modern, modular TypeScript project for HealthCore data analytics, validation, and reporting. This project demonstrates all assignment goals and optional features for Milestone 2.

## Features

- TypeScript interfaces for Claim, Appointment, Clinician, Location
- Utility functions for filtering, searching, analytics, and validation
- Modern web UI (TailwindCSS) for demo/testing
- Sample data for all entities
- Meets all assignment and optional goals

## Getting Started

1. **Install dependencies:**

   ```sh
   npm install
   ```

2. **Build TypeScript:**

   ```sh
   npm run build
   ```

3. **Start local server:**

   ```sh
   npm start
   ```

   Then open [http://localhost:3000](http://localhost:3000) (or the port shown) to view the demo.

## Project Structure

- `src/types/models.ts` — TypeScript interfaces
- `src/utils/` — Utility functions (collections, search, transformations, validations)
- `src/index.html` — Main UI
- `src/dashboard.js` — UI logic and demo

## Milestone 4: Incident CSV Analysis (Script + API + Web)

### Phase 1: Script (`scripts/analyze.py`)

Run from the repository root:

```sh
C:/Users/alexw/AppData/Local/Programs/Python/Python311/python.exe scripts/analyze.py scripts/incidents-COMPANY.csv
```

What it does:

- Accepts CSV path as a CLI argument
- Loads and validates records (missing required fields, invalid category/status, out-of-range satisfaction)
- Excludes invalid records from metric calculations
- Prints readable summary (totals, category breakdown, status breakdown, invalid-reason breakdown, average satisfaction for closed cases with score)
- Prompts `Export results to CSV? [y / n]`
- If `y`, writes `scripts/results.csv`
- Verifies computed summary against `scripts/expected-results.json`

### Phase 2: API (`services/api`)

```sh
cd services/api
C:/Users/alexw/AppData/Local/Programs/Python/Python311/python.exe -m pip install -r requirements.txt
C:/Users/alexw/AppData/Local/Programs/Python/Python311/python.exe -m uvicorn main:app --reload --port 8000
```

Endpoints:

- `POST /api/incidents/analyze` (`multipart/form-data`, field name `file`) -> returns JSON summary + invalid-record detail
- `GET /api/incidents/results/export` -> returns downloadable `results.csv` for the most recent analysis

Error responses:

- Empty upload -> HTTP 400
- Non-CSV file extension -> HTTP 400
- Invalid CSV format/encoding -> HTTP 400
- Export before analysis -> HTTP 404

### Web UI (`uis/web`)

```sh
cd uis/web
C:/Users/alexw/AppData/Local/Programs/Python/Python311/python.exe -m http.server 5500
```

Open `http://localhost:5500`.

Capabilities:

- Incident analysis page with menu entry
- Drag/drop or file-select CSV upload
- Calls the API analyze endpoint
- Displays summary metrics, category/status breakdowns, and invalid-record type counts
- Download button for exported CSV

### Included Assignment Assets

- Sample 100-record file: `scripts/incidents-COMPANY.csv`
- Expected summary for exact verification: `scripts/expected-results.json`

## Assignment Goals Checklist

- [x] TypeScript interfaces for all entities
- [x] Utility functions for filtering, searching, analytics, validation
- [x] Modern, responsive web UI
- [x] Sample data for all entities
- [x] Meets all assignment and optional goals

## License

MIT
