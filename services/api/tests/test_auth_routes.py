from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import HTTPException, status

from auth_models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UserRole,
)


def test_login_happy_path_returns_bearer_token(monkeypatch, user_factory, auth_routes):
    user = user_factory(email="jane@example.com", role=UserRole.ADMIN)

    seen: dict[str, object] = {}

    def fake_get_user_by_email(email: str):
        seen["email"] = email
        return user

    monkeypatch.setattr(auth_routes.UserService, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_routes, "verify_password", lambda plain, hashed: plain == "correct-horse" and hashed == "hashed-password")
    monkeypatch.setattr(auth_routes, "create_access_token", lambda **kwargs: f"token-for-{kwargs['user_id']}")

    result = auth_routes.login(LoginRequest(email="  jane@example.com  ", password="correct-horse"))

    assert result.access_token == "token-for-1"
    assert result.token_type == "bearer"
    assert seen["email"] == "jane@example.com"


def test_login_edge_case_strips_email_whitespace(monkeypatch, user_factory, auth_routes):
    user = user_factory(email="edge@example.com")
    captured: list[str] = []

    monkeypatch.setattr(auth_routes.UserService, "get_user_by_email", lambda email: captured.append(email) or user)
    monkeypatch.setattr(auth_routes, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth_routes, "create_access_token", lambda **kwargs: "token")

    result = auth_routes.login(LoginRequest(email="  edge@example.com  ", password="password1"))

    assert result.access_token == "token"
    assert captured == ["edge@example.com"]


def test_login_failure_when_credentials_do_not_match(monkeypatch, auth_routes):
    monkeypatch.setattr(auth_routes.UserService, "get_user_by_email", lambda _email: None)

    with pytest.raises(HTTPException) as exc_info:
        auth_routes.login(LoginRequest(email="missing@example.com", password="password1"))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid credentials."


def test_me_happy_path_returns_profile_payload(monkeypatch, user_factory, profile_factory, auth_routes):
    user = user_factory(email="user@example.com")
    profile = profile_factory(user_id=user.id)

    monkeypatch.setattr(auth_routes.UserService, "get_profile_for_user", lambda user_id: profile if user_id == user.id else None)

    result = auth_routes.me(user)

    assert result.email == "user@example.com"
    assert result.profile is not None
    assert result.profile.name == "Alice"


def test_me_edge_case_returns_null_profile_when_none_exists(monkeypatch, user_factory, auth_routes):
    user = user_factory(email="noprofile@example.com")
    monkeypatch.setattr(auth_routes.UserService, "get_profile_for_user", lambda _user_id: None)

    result = auth_routes.me(user)

    assert result.email == "noprofile@example.com"
    assert result.profile is None


def test_me_failure_mode_is_rejected_before_route_logic(monkeypatch, auth_routes, auth_security):
    from fastapi.security import HTTPAuthorizationCredentials

    monkeypatch.setattr(auth_routes.UserService, "get_user_by_id", lambda _user_id: None)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

    with pytest.raises(HTTPException) as exc_info:
        auth_security.get_current_user(credentials)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_forgot_password_happy_path_creates_token_and_sends_email(monkeypatch, user_factory, auth_routes):
    user = user_factory(email="notify@example.com")
    calls: dict[str, object] = {}

    monkeypatch.setattr(auth_routes.UserService, "get_user_by_email", lambda _email: user)
    monkeypatch.setattr(auth_routes, "create_password_reset_token", lambda **kwargs: "reset-token")
    monkeypatch.setattr(auth_routes.UserService, "create_password_reset_token_record", lambda **kwargs: calls.update(kwargs))
    monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda **kwargs: calls.update({"email": kwargs}) or True)

    result = auth_routes.forgot_password(ForgotPasswordRequest(email="notify@example.com"))

    assert result.message == auth_routes.RESET_PASSWORD_CONFIRMATION_MESSAGE
    assert calls["token_id"]
    assert calls["user_id"] == user.id
    assert isinstance(calls["expires_at"], datetime)
    assert calls["email"] == {"recipient_email": user.email, "reset_token": "reset-token"}


def test_forgot_password_edge_case_suppresses_missing_user(monkeypatch, auth_routes):
    token_calls = []
    email_calls = []
    monkeypatch.setattr(auth_routes.UserService, "get_user_by_email", lambda _email: None)
    monkeypatch.setattr(auth_routes, "create_password_reset_token", lambda **kwargs: token_calls.append(kwargs))
    monkeypatch.setattr(auth_routes.UserService, "create_password_reset_token_record", lambda **kwargs: token_calls.append(kwargs))
    monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda **kwargs: email_calls.append(kwargs) or True)

    result = auth_routes.forgot_password(ForgotPasswordRequest(email="missing@example.com"))

    assert result.message == auth_routes.RESET_PASSWORD_CONFIRMATION_MESSAGE
    assert token_calls == []
    assert email_calls == []


def test_forgot_password_failure_mode_still_returns_generic_confirmation(monkeypatch, user_factory, auth_routes):
    user = user_factory(email="failure@example.com")
    token_calls = []
    email_calls = []

    monkeypatch.setattr(auth_routes.UserService, "get_user_by_email", lambda _email: user)
    monkeypatch.setattr(auth_routes, "create_password_reset_token", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(auth_routes.UserService, "create_password_reset_token_record", lambda **kwargs: token_calls.append(kwargs))
    monkeypatch.setattr(auth_routes, "send_password_reset_email", lambda **kwargs: email_calls.append(kwargs) or True)

    result = auth_routes.forgot_password(ForgotPasswordRequest(email="failure@example.com"))

    assert result.message == auth_routes.RESET_PASSWORD_CONFIRMATION_MESSAGE
    assert token_calls == []
    assert email_calls == []


def test_reset_password_happy_path_consumes_token_and_updates_password(monkeypatch, user_factory, auth_routes):
    user = user_factory(email="reset@example.com")
    captured: dict[str, object] = {}

    monkeypatch.setattr(auth_routes, "decode_password_reset_token", lambda _token: {"purpose": "reset_password", "sub": str(user.id), "jti": "token-1"})
    monkeypatch.setattr(auth_routes.UserService, "consume_password_reset_token", lambda **kwargs: kwargs == {"token_id": "token-1", "user_id": user.id})
    monkeypatch.setattr(auth_routes.UserService, "get_user_by_id", lambda user_id: user if user_id == user.id else None)
    monkeypatch.setattr(auth_routes, "hash_password", lambda password: f"hashed::{password}")
    monkeypatch.setattr(auth_routes.UserService, "update_user", lambda user_id, updates: captured.update({"user_id": user_id, "updates": updates}))

    result = auth_routes.reset_password(ResetPasswordRequest(token="token-value", new_password="new-password"))

    assert result.message == "Password reset successful."
    assert captured == {"user_id": user.id, "updates": {"hashed_password": "hashed::new-password"}}


def test_reset_password_edge_case_rejects_token_with_wrong_purpose(monkeypatch, auth_routes):
    monkeypatch.setattr(auth_routes, "decode_password_reset_token", lambda _token: {"purpose": "session", "sub": "1", "jti": "token-1"})

    with pytest.raises(HTTPException) as exc_info:
        auth_routes.reset_password(ResetPasswordRequest(token="token-value", new_password="new-password"))

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Invalid or expired reset token."


def test_reset_password_failure_mode_rejects_expired_or_used_token(monkeypatch, auth_routes):
    monkeypatch.setattr(auth_routes, "decode_password_reset_token", lambda _token: {"purpose": "reset_password", "sub": "1", "jti": "token-1"})
    monkeypatch.setattr(auth_routes.UserService, "consume_password_reset_token", lambda **kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        auth_routes.reset_password(ResetPasswordRequest(token="token-value", new_password="new-password"))

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Invalid or expired reset token."


def test_change_password_happy_path_updates_password(monkeypatch, user_factory, auth_routes):
    current_user = user_factory(hashed_password="stored-hash")
    seen: dict[str, object] = {}

    def fake_verify_password(plain_password: str, hashed_password: str) -> bool:
        seen["verify"] = (plain_password, hashed_password)
        return True

    monkeypatch.setattr(auth_routes, "verify_password", fake_verify_password)
    monkeypatch.setattr(auth_routes, "hash_password", lambda password: f"hashed::{password}")
    monkeypatch.setattr(auth_routes.UserService, "update_user", lambda user_id, updates: seen.update({"user_id": user_id, "updates": updates}))

    result = auth_routes.change_password(
        ChangePasswordRequest(current_password="current-password", new_password="new-password"),
        current_user,
    )

    assert result.message == "Password changed successfully."
    assert seen["verify"] == ("current-password", "stored-hash")
    assert seen["user_id"] == current_user.id
    assert seen["updates"] == {"hashed_password": "hashed::new-password"}


def test_change_password_edge_case_strips_whitespace_before_verification(monkeypatch, user_factory, auth_routes):
    current_user = user_factory(hashed_password="stored-hash")
    seen: dict[str, object] = {}

    def fake_verify_password(plain_password: str, hashed_password: str) -> bool:
        seen["verify"] = (plain_password, hashed_password)
        return True

    monkeypatch.setattr(auth_routes, "verify_password", fake_verify_password)
    monkeypatch.setattr(auth_routes, "hash_password", lambda password: f"hashed::{password}")
    monkeypatch.setattr(auth_routes.UserService, "update_user", lambda user_id, updates: seen.update({"user_id": user_id, "updates": updates}))

    result = auth_routes.change_password(
        ChangePasswordRequest(current_password=" current-password ", new_password=" new-password "),
        current_user,
    )

    assert result.message == "Password changed successfully."
    assert seen["verify"] == ("current-password", "stored-hash")
    assert seen["updates"] == {"hashed_password": "hashed::new-password"}


def test_change_password_failure_mode_rejects_wrong_current_password(monkeypatch, user_factory, auth_routes):
    current_user = user_factory(hashed_password="stored-hash")
    monkeypatch.setattr(auth_routes, "verify_password", lambda _plain, _hashed: False)

    with pytest.raises(HTTPException) as exc_info:
        auth_routes.change_password(
            ChangePasswordRequest(current_password="wrong-password", new_password="new-password"),
            current_user,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Current password is incorrect."
