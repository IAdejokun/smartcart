"""Password hashing — bcrypt via passlib.

Wrapped behind a thin interface so we can swap to argon2id later without
touching every callsite. Modern guidance (OWASP 2023+) actually prefers
argon2id, but bcrypt remains acceptable when configured with rounds >= 12.
"""
from __future__ import annotations

from passlib.context import CryptContext

from app.config import settings


_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password. Bcrypt salts internally — no salt management needed."""
    return _pwd_context.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Constant-time password verification. Returns False for any mismatch or malformed hash."""
    try:
        return _pwd_context.verify(plaintext, hashed)
    except Exception:
        # passlib raises on malformed hashes — treat as auth failure, never propagate
        return False