"""Authentication dependencies — FastAPI Depends() functions.

Three tiers, mapping to the Zero Trust microsegmentation pattern from
SecureVault:
- get_optional_current_user: Public routes that personalise if logged in
- get_current_user: Authenticated routes (everything that mutates user data)
- get_current_active_user: Authenticated AND not soft-deactivated
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security.jwt_handler import decode_token


# tokenUrl is the relative path FastAPI's Swagger UI uses for the "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolves the current user from a Bearer token. 401 if missing or invalid."""
    if token is None:
        raise _credentials_exception

    try:
        payload = decode_token(token, expected_type="access")
        user_id = UUID(payload.sub)
    except (JWTError, ValueError):
        raise _credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise _credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Resolves the current user AND ensures they're active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Like get_current_user, but returns None instead of raising on missing/invalid token.

    Use this on routes that personalise for logged-in users but still serve
    anonymous traffic — e.g. the /recommendations endpoint, which can return
    popularity-ranked products to anonymous users and DRL recommendations to
    authenticated ones.
    """
    if token is None:
        return None

    try:
        payload = decode_token(token, expected_type="access")
        user_id = UUID(payload.sub)
    except (JWTError, ValueError):
        return None

    return db.get(User, user_id)