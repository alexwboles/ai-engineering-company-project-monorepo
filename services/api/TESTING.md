# Testing

This FastAPI project uses `pytest` for the authentication API test suite.

## How to run

From `services/api`:

```bash
uv run pytest
```

To run with coverage:

```bash
uv run pytest --cov --cov-report=term-missing
```

Current result from the latest run:

- 22 tests passed
- Coverage on the authentication files: 83% total

## What the suite covers

- `auth_security.py`
  - Token generation and decoding
  - Password verification helpers
  - `get_current_user` success and failure handling
- `routes/auth.py`
  - `POST /auth/login`
  - `GET /auth/me`
  - `POST /auth/forgot-password`
  - `POST /auth/reset-password`
  - `POST /auth/change-password`

## Case plan

Each endpoint is covered with:

- One happy-path test
- One edge-case test
- One failure-mode test

Edge cases in this suite focus on input normalization and null/empty outcomes, while failure-mode tests focus on rejected credentials, malformed tokens, or expired-used reset tokens.

## Notes

- The tests call the route and helper functions directly.
- They do not test HTTP serialization or FastAPI request plumbing.
- Environment variables required by authentication helpers are set in `tests/conftest.py` for the test run.
- Coverage is configured to focus on the authentication modules rather than unrelated backend helpers.
