"""Authentication endpoints for HospitalFlow Phase 9A."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.dependencies import current_user
from backend.services import auth

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: str
    username: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = auth.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(
        access_token=auth.create_access_token(user),
        expires_in_minutes=auth.TOKEN_EXPIRE_MINUTES,
        user=UserResponse(**user),
    )


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user["sub"], username=user["username"], role=user["role"])
