from __future__ import annotations

from fastapi import APIRouter, Depends

try:
    from services.api.auth_models import ProfileResponse, ProfileUpdate
    from services.api.auth_security import get_current_user
    from services.api.user_service import UserService
except ModuleNotFoundError:
    from auth_models import ProfileResponse, ProfileUpdate
    from auth_security import get_current_user
    from user_service import UserService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user=Depends(get_current_user)) -> ProfileResponse:
    profile = UserService.get_profile_for_user(current_user.id)
    if profile is None:
        created = UserService.update_profile_for_user(
            current_user.id,
            {
                "name": "",
                "phone": "",
                "address": "",
            },
        )
        return ProfileResponse.model_validate(created.model_dump())

    return ProfileResponse.model_validate(profile.model_dump())


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(payload: ProfileUpdate, current_user=Depends(get_current_user)) -> ProfileResponse:
    profile = UserService.update_profile_for_user(current_user.id, payload.model_dump(exclude_none=True))
    return ProfileResponse.model_validate(profile.model_dump())
