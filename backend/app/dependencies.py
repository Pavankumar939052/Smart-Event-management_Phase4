
from fastapi import Depends, HTTPException
from app.auth import get_current_user
from app.models import User

VALID_ROLES = {"USER", "ORGANIZER", "ADMIN"}


def require_role(*allowed_roles: str):
    allowed = {role.upper() for role in allowed_roles}

    invalid_roles = allowed - VALID_ROLES
    if invalid_roles:
        raise ValueError(f"Invalid roles: {invalid_roles}")

    def role_checker(
        current_user: User = Depends(get_current_user),
    ):
        user_role = (current_user.role or "USER").upper()

        if user_role not in allowed:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_checker

