from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from src.auth.security import CurrentUser, decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2)) -> CurrentUser:
    return decode_token(token)


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise HTTPException(403, "Only admins can do this")
    return user
