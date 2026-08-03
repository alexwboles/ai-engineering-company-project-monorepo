from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError

try:
    from services.api.auth_models import (
        AuthMeResponse,
        ChangePasswordRequest,
        ForgotPasswordRequest,
        LoginRequest,
        MessageResponse,
        ProfileResponse,
        ResetPasswordRequest,
        TokenResponse,
    )
    from services.api.auth_security import (
        create_access_token,
        create_password_reset_token,
        decode_password_reset_token,
        get_reset_token_expire_minutes,
        get_current_user,
        hash_password,
        verify_password,
    )
    from services.api.email_service import send_password_reset_email
    from services.api.user_service import UserService
except ModuleNotFoundError:
    from auth_models import (
        AuthMeResponse,
        ChangePasswordRequest,
        ForgotPasswordRequest,
        LoginRequest,
        MessageResponse,
        ProfileResponse,
        ResetPasswordRequest,
        TokenResponse,
    )
    from auth_security import (
        create_access_token,
        create_password_reset_token,
        decode_password_reset_token,
        get_reset_token_expire_minutes,
        get_current_user,
        hash_password,
        verify_password,
    )
    from email_service import send_password_reset_email
    from user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])
RESET_PASSWORD_CONFIRMATION_MESSAGE = "If that address is registered, you will receive a reset link shortly."


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = UserService.get_user_by_email(str(payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AuthMeResponse)
def me(current_user=Depends(get_current_user)) -> AuthMeResponse:
    profile = UserService.get_profile_for_user(current_user.id)
    profile_payload = None
    if profile is not None:
        profile_payload = ProfileResponse.model_validate(profile.model_dump())

    return AuthMeResponse(email=current_user.email, role=current_user.role, profile=profile_payload)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest) -> MessageResponse:
    user = UserService.get_user_by_email(str(payload.email))

    if user is not None:
        try:
            token_id = str(uuid4())
            token = create_password_reset_token(user_id=user.id, email=user.email, token_id=token_id)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=get_reset_token_expire_minutes())
            UserService.create_password_reset_token_record(token_id=token_id, user_id=user.id, expires_at=expires_at)
            send_password_reset_email(recipient_email=user.email, reset_token=token)
        except Exception:
            # Keep response constant to avoid user enumeration.
            pass

    return MessageResponse(message=RESET_PASSWORD_CONFIRMATION_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest) -> MessageResponse:
    try:
        token_payload = decode_password_reset_token(payload.token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    purpose = token_payload.get("purpose")
    subject = token_payload.get("sub")
    token_id = token_payload.get("jti")
    if purpose != "reset_password" or subject is None or token_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    token_was_consumed = UserService.consume_password_reset_token(token_id=str(token_id), user_id=user_id)
    if not token_was_consumed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    user = UserService.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    UserService.update_user(user_id, {"hashed_password": hash_password(payload.new_password)})
    return MessageResponse(message="Password reset successful.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user)) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")

    UserService.update_user(current_user.id, {"hashed_password": hash_password(payload.new_password)})
    return MessageResponse(message="Password changed successfully.")
