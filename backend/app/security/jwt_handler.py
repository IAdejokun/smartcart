"""JWT handling — access tokens, refresh tokens, refresh rotation.

Refresh rotation pattern (NIST SP 800-63B aligned):
- Each refresh token contains a `jti` (JWT ID — random UUID).
- On refresh, the old refresh token is invalidated and a new one is issued.
- Reuse of an invalidated refresh token is a strong signal of theft and
  triggers a session-wide revocation.

For MVP, the revocation list is in-memory. For production, swap to Redis.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from app.config import settings


class TokenPayload(BaseModel):
    sub: str            # User ID as string
    type: str           # "access" or "refresh"
    jti: str            # Token ID — used for revocation
    exp: int            # Expiry (epoch seconds)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# In-memory revocation list. Replace with Redis in production.
_revoked_jtis: set[str] = set()


def _create_token(*, user_id: UUID, token_type: str, expires_delta: timedelta) -> tuple[str, str]:
    """Returns (encoded_token, jti). The jti is returned so callers can store it for rotation."""
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": jti,
        "exp": int(expire.timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded, jti


def create_access_token(user_id: UUID) -> tuple[str, str]:
    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID) -> tuple[str, str]:
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def create_token_pair(user_id: UUID) -> tuple[TokenPair, str, str]:
    """Returns (TokenPair, access_jti, refresh_jti)."""
    access_token, access_jti = create_access_token(user_id)
    refresh_token, refresh_jti = create_refresh_token(user_id)
    return (
        TokenPair(access_token=access_token, refresh_token=refresh_token),
        access_jti,
        refresh_jti,
    )


def decode_token(token: str, expected_type: str) -> TokenPayload:
    """Decode and validate a token. Raises JWTError on any failure.

    expected_type prevents access-token-as-refresh-token confusion attacks.
    """
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        payload = TokenPayload(**raw)
    except (JWTError, ValidationError) as e:
        raise JWTError(f"Invalid token: {e}") from e

    if payload.type != expected_type:
        raise JWTError(f"Wrong token type: expected {expected_type}, got {payload.type}")

    if payload.jti in _revoked_jtis:
        raise JWTError("Token has been revoked")

    return payload


def revoke_jti(jti: str) -> None:
    """Add a JTI to the revocation list. Idempotent."""
    _revoked_jtis.add(jti)