import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from fastapi import HTTPException
from src.utils.settings import settings

SCRYPT = {"n": 2**14, "r": 8, "p": 1}


@dataclass
class CurrentUser:
    id: UUID
    email: str
    name: str
    role: str


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user) -> str:
    """The token carries id, name and role so requests need no database lookup. A removed user keeps access until it expires."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    claims = {"sub": str(user.id), "email": user.email, "name": user.name, "role": user.role, "exp": expires}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> CurrentUser:
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return CurrentUser(id=UUID(claims["sub"]), email=claims["email"], name=claims["name"], role=claims["role"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired login", headers={"WWW-Authenticate": "Bearer"})
