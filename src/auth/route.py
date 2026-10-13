from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.auth.controller import AuthController
from src.auth.deps import get_current_user
from src.auth.dtos import TokenResponse, UserResponse
from src.auth.security import CurrentUser
from src.utils.db import get_db

auth_routes = APIRouter(prefix="/auth", tags=["auth"])


@auth_routes.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return AuthController.login(db, form.username, form.password)


@auth_routes.get("/me", response_model=UserResponse)
def me(user: CurrentUser = Depends(get_current_user)):
    return user
