"""Authentication endpoints: register, login, refresh, me.

The refresh-rotation pattern: each /refresh call invalidates the old refresh
token's JTI and issues a new pair. Reuse of an old refresh token is logged
(and in production should trigger a session-wide revocation alert).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from fastapi.security import OAuth2PasswordRequestForm

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security.dependencies import get_current_active_user
from app.security.jwt_handler import (
    create_token_pair,
    decode_token,
    revoke_jti,
)
from app.security.password import hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    user = User(
        email=payload.email.lower(),                # Normalise for uniqueness
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    # Constant-time-ish: always run verify_password even if user is None,
    # to prevent timing-based user enumeration. Use a dummy hash.
    dummy_hash = "$2b$12$" + "x" * 53
    valid = verify_password(payload.password, user.password_hash if user else dummy_hash)

    if not user or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    pair, _access_jti, _refresh_jti = create_token_pair(user.id)
    return TokenResponse(**pair.model_dump())


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = db.get(User, token_payload.sub)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer valid",
        )

    # Rotation: revoke the old refresh token, issue a new pair
    revoke_jti(token_payload.jti)

    pair, _access_jti, _refresh_jti = create_token_pair(user.id)
    return TokenResponse(**pair.model_dump())

@router.post("/token", response_model=TokenResponse)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """OAuth2-compatible form login — used by Swagger UI's Authorize flow.

    Real clients use POST /auth/login with a JSON body. This endpoint exists
    so the /docs 'Authorize' button works without forcing the entire frontend
    to speak form-encoded.

    Note: OAuth2 spec calls the field 'username' even though we treat it as email.
    """
    user = db.scalar(select(User).where(User.email == form_data.username.lower()))

    dummy_hash = "$2b$12$" + "x" * 53
    valid = verify_password(form_data.password, user.password_hash if user else dummy_hash)

    if not user or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    pair, _, _ = create_token_pair(user.id)
    return TokenResponse(**pair.model_dump())

@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_active_user)) -> User:
    """Returns the authenticated user. Used by the frontend to bootstrap session state."""
    return current_user