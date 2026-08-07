from __future__ import annotations

import sys
import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
for path in (REPO_ROOT, API_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(autouse=True)
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("RESET_TOKEN_SECRET_KEY", "test-reset-secret")
    monkeypatch.setenv("RESET_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("FRONTEND_RESET_PASSWORD_URL", "http://localhost:3000/reset-password")


@pytest.fixture
def user_factory():
    from auth_models import UserRecord, UserRole

    def _make(
        *,
        user_id: int = 1,
        email: str = "alice@example.com",
        hashed_password: str = "hashed-password",
        is_active: bool = True,
        role: UserRole = UserRole.USER,
        created_at: datetime | None = None,
    ) -> UserRecord:
        return UserRecord(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
            role=role,
            created_at=created_at or datetime(2026, 8, 3, tzinfo=timezone.utc),
        )

    return _make


@pytest.fixture
def profile_factory():
    from auth_models import ProfileRecord

    def _make(
        *,
        profile_id: int = 11,
        user_id: int = 1,
        name: str = "Alice",
        phone: str = "555-0100",
        address: str = "123 Health St",
    ) -> ProfileRecord:
        return ProfileRecord(id=profile_id, user_id=user_id, name=name, phone=phone, address=address)

    return _make


@pytest.fixture
def auth_routes():
    return importlib.import_module("services.api.routes.auth")


@pytest.fixture
def auth_security():
    return importlib.import_module("services.api.auth_security")
