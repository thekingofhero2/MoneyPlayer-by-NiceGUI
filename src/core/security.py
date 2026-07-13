from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt
from passlib.context import CryptContext
from src.core.config import settings
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    """Generates a JWT access token for a specific user ID with a defined expiration time."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_safe_pwd_bytes(password: str) -> bytes:
    # 先sha256摘要，输出固定32字节，永远<72
    return hashlib.sha256(password.encode("utf-8")).digest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares a plain text password with a hashed password to check for a match."""
    safe_bytes = get_safe_pwd_bytes(plain_password)
    return pwd_context.verify(safe_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """Computes the bcrypt hash of a plain text password."""
    safe_bytes = get_safe_pwd_bytes(password)
    return pwd_context.hash(safe_bytes)
