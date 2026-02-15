"""
Security utilities: JWT tokens, password hashing, credential encryption.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import settings


# ── Password Hashing ────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT Tokens ───────────────────────────────────────────────
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token. Returns None on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ── Credential Encryption (Fernet) ──────────────────────────
def _get_fernet() -> Fernet:
    """Get a Fernet instance using the configured encryption key."""
    key = settings.CREDENTIAL_ENCRYPTION_KEY.encode()
    # Pad / truncate to 32 bytes then base64 for Fernet
    import base64
    key_bytes = key.ljust(32, b"0")[:32]
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_credentials(plaintext: str) -> str:
    """Encrypt a plaintext string (e.g. JSON credentials)."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_credentials(ciphertext: str) -> str:
    """Decrypt an encrypted credential string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
