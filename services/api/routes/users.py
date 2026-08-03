from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

try:
    from services.api.auth_models import UserCreate, UserResponse, UserRole, UserUpdate
    from services.api.auth_security import get_current_user, hash_password
    from services.api.user_service import UserService
except ModuleNotFoundError:
    from auth_models import UserCreate, UserResponse, UserRole, UserUpdate
    from auth_security import get_current_user, hash_password
    from user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate) -> UserResponse:
    if payload.role != UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration can only create users with role 'user'.",
        )

    user, _profile = UserService.create_user(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.USER,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
    )
    return UserResponse.model_validate(user.model_dump())


@router.get("", response_model=list[UserResponse])
def list_users(current_user=Depends(get_current_user)) -> list[UserResponse]:
    _ = current_user
    return [UserResponse.model_validate(user.model_dump()) for user in UserService.list_users()]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user=Depends(get_current_user)) -> UserResponse:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    user = UserService.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserResponse.model_validate(user.model_dump())


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, current_user=Depends(get_current_user)) -> UserResponse:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    updates = payload.model_dump(exclude_none=True)

    if "role" in updates:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can change role.")
        updates["role"] = updates["role"].value

    if "password" in updates:
        updates["hashed_password"] = hash_password(str(updates.pop("password")))

    if "email" in updates:
        updates["email"] = str(updates["email"]).strip().lower()
        existing = UserService.get_user_by_email(str(updates["email"]))
        if existing is not None and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    updated = UserService.update_user(user_id, updates)
    return UserResponse.model_validate(updated.model_dump())


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, current_user=Depends(get_current_user)) -> dict[str, str]:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    UserService.delete_user(user_id)
    return {"message": "User deleted."}
