from uuid import UUID
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
