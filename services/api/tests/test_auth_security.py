from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt


def test_create_access_token_happy_path_encodes_expected_claims(auth_security):
    token = auth_security.create_access_token(user_id=7, email="user@example.com", role="admin")

    payload = jwt.decode(token, "test-jwt-secret", algorithms=["HS256"])
    assert payload["sub"] == "7"
    assert payload["email"] == "user@example.com"
    assert payload["role"] == "admin"
    assert payload["exp"] > int(datetime.now(timezone.utc).timestamp())


def test_create_access_token_rejects_invalid_expiration_env(monkeypatch: pytest.MonkeyPatch, auth_security):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "zero")

    with pytest.raises(RuntimeError, match="ACCESS_TOKEN_EXPIRE_MINUTES must be an integer"):
        auth_security.create_access_token(user_id=1, email="user@example.com", role="user")


def test_create_password_reset_token_happy_path_and_decode(auth_security):
    token = auth_security.create_password_reset_token(user_id=9, email="reset@example.com", token_id="token-123")

    payload = auth_security.decode_password_reset_token(token)
    assert payload["sub"] == "9"
    assert payload["email"] == "reset@example.com"
    assert payload["purpose"] == "reset_password"
    assert payload["jti"] == "token-123"


def test_decode_password_reset_token_rejects_malformed_token(auth_security):
    with pytest.raises(JWTError):
        auth_security.decode_password_reset_token("not-a-real-token")


def test_get_current_user_happy_path_returns_the_matching_user(monkeypatch, user_factory, auth_security):
    user = user_factory()
    token = auth_security.create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    monkeypatch.setattr(auth_security.UserService, "get_user_by_id", lambda user_id: user if user_id == user.id else None)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = auth_security.get_current_user(credentials)

    assert result == user


def test_get_current_user_rejects_missing_credentials(auth_security):
    with pytest.raises(HTTPException) as exc_info:
        auth_security.get_current_user(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated."


def test_get_current_user_rejects_invalid_or_expired_token(monkeypatch, auth_security):
    monkeypatch.setattr(auth_security.UserService, "get_user_by_id", lambda _user_id: None)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

    with pytest.raises(HTTPException) as exc_info:
        auth_security.get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid or expired token."
