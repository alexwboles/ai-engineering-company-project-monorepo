from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

try:
    from services.api.auth_models import AuthMeResponse, LoginRequest, ProfileResponse, TokenResponse
    from services.api.auth_security import create_access_token, get_current_user, verify_password
    from services.api.user_service import UserService
except ModuleNotFoundError:
    from auth_models import AuthMeResponse, LoginRequest, ProfileResponse, TokenResponse
    from auth_security import create_access_token, get_current_user, verify_password
    from user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


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
