import time
from collections import defaultdict, deque
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.auth.model import User
from src.auth.security import create_token, hash_password, verify_password
from src.auth.dtos import TokenResponse, UserResponse

MAX_FAILURES, WINDOW_SECONDS = 5, 300
failures: dict[str, deque] = defaultdict(deque)   # recent failed logins per email (in memory)
DUMMY_HASH = hash_password("not-a-real-password")


class AuthController:
    @staticmethod
    def login(db: Session, email: str, password: str) -> TokenResponse:
        email = email.strip().lower()
        recent = failures[email]
        while recent and time.time() - recent[0] > WINDOW_SECONDS:
            recent.popleft()
        if len(recent) >= MAX_FAILURES:
            raise HTTPException(429, "Too many failed logins. Try again in a few minutes.")

        user = db.query(User).filter(User.email == email).first()
        valid = verify_password(password, user.password_hash if user else DUMMY_HASH)   # same work either way
        if not user or not valid:
            recent.append(time.time())
            raise HTTPException(401, "Wrong email or password", headers={"WWW-Authenticate": "Bearer"})

        recent.clear()
        return TokenResponse(access_token=create_token(user), user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role))

    @staticmethod
    def create_user(db: Session, email: str, name: str, password: str, role: str) -> User:
        if role not in ("admin", "viewer"):
            raise ValueError("role must be admin or viewer")
        user = User(email=email.strip().lower(), name=name, password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        return user
