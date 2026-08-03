from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from tinydb import Query

try:
    from services.api.auth_models import ProfileRecord, UserRecord, UserRole
    from services.api.database import get_auth_db
except ModuleNotFoundError:
    from auth_models import ProfileRecord, UserRecord, UserRole
    from database import get_auth_db


class UserService:
    @staticmethod
    def create_user(
        *,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        name: str | None = None,
        phone: str | None = None,
        address: str | None = None,
    ) -> tuple[UserRecord, ProfileRecord]:
        now = datetime.now(timezone.utc)
        normalized_email = email.strip().lower()
        user_query = Query()

        with get_auth_db() as db:
            users = db.table("users")
            profiles = db.table("profiles")
            existing = users.get(user_query.email == normalized_email)
            if existing is not None:
                raise HTTPException(status_code=409, detail="Email already registered.")

            user_doc_id = users.insert(
                {
                    "email": normalized_email,
                    "hashed_password": hashed_password,
                    "is_active": is_active,
                    "role": role.value,
                    "created_at": now.isoformat(),
                }
            )

            profile_doc_id = profiles.insert(
                {
                    "user_id": user_doc_id,
                    "name": (name or "").strip(),
                    "phone": (phone or "").strip(),
                    "address": (address or "").strip(),
                }
            )

            user = users.get(doc_id=user_doc_id)
            profile = profiles.get(doc_id=profile_doc_id)

        if user is None or profile is None:
            raise HTTPException(status_code=500, detail="Unable to create user.")

        return _to_user_record(user_doc_id, user), _to_profile_record(profile_doc_id, profile)

    @staticmethod
    def get_user_by_id(user_id: int) -> UserRecord | None:
        with get_auth_db() as db:
            users = db.table("users")
            row = users.get(doc_id=user_id)

        if row is None:
            return None

        return _to_user_record(user_id, row)

    @staticmethod
    def get_user_by_email(email: str) -> UserRecord | None:
        user_query = Query()
        normalized_email = email.strip().lower()

        with get_auth_db() as db:
            users = db.table("users")
            row = users.get(user_query.email == normalized_email)

        if row is None:
            return None

        return _to_user_record(row.doc_id, row)

    @staticmethod
    def list_users() -> list[UserRecord]:
        with get_auth_db() as db:
            users = db.table("users")
            rows = users.all()

        return [_to_user_record(row.doc_id, row) for row in rows]

    @staticmethod
    def update_user(user_id: int, updates: dict[str, object]) -> UserRecord:
        with get_auth_db() as db:
            users = db.table("users")
            existing = users.get(doc_id=user_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="User not found.")

            users.update(updates, doc_ids=[user_id])
            updated = users.get(doc_id=user_id)

        if updated is None:
            raise HTTPException(status_code=404, detail="User not found.")

        return _to_user_record(user_id, updated)

    @staticmethod
    def delete_user(user_id: int) -> None:
        profile_query = Query()

        with get_auth_db() as db:
            users = db.table("users")
            profiles = db.table("profiles")
            existing = users.get(doc_id=user_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="User not found.")

            users.remove(doc_ids=[user_id])
            profiles.remove(profile_query.user_id == user_id)

    @staticmethod
    def get_profile_for_user(user_id: int) -> ProfileRecord | None:
        profile_query = Query()

        with get_auth_db() as db:
            profiles = db.table("profiles")
            row = profiles.get(profile_query.user_id == user_id)

        if row is None:
            return None

        return _to_profile_record(row.doc_id, row)

    @staticmethod
    def update_profile_for_user(user_id: int, updates: dict[str, object]) -> ProfileRecord:
        profile_query = Query()

        with get_auth_db() as db:
            profiles = db.table("profiles")
            row = profiles.get(profile_query.user_id == user_id)
            if row is None:
                profile_doc_id = profiles.insert(
                    {
                        "user_id": user_id,
                        "name": "",
                        "phone": "",
                        "address": "",
                    }
                )
                row = profiles.get(doc_id=profile_doc_id)
                if row is None:
                    raise HTTPException(status_code=500, detail="Unable to create profile.")

            profile_id = row.doc_id
            profiles.update(updates, doc_ids=[profile_id])
            updated = profiles.get(doc_id=profile_id)

        if updated is None:
            raise HTTPException(status_code=404, detail="Profile not found.")

        return _to_profile_record(profile_id, updated)


def _to_user_record(doc_id: int, row: dict[str, object]) -> UserRecord:
    return UserRecord.model_validate(
        {
            "id": doc_id,
            "email": row["email"],
            "hashed_password": row["hashed_password"],
            "is_active": row["is_active"],
            "role": row["role"],
            "created_at": row["created_at"],
        }
    )


def _to_profile_record(doc_id: int, row: dict[str, object]) -> ProfileRecord:
    return ProfileRecord.model_validate(
        {
            "id": doc_id,
            "user_id": row["user_id"],
            "name": row.get("name", ""),
            "phone": row.get("phone", ""),
            "address": row.get("address", ""),
        }
    )
