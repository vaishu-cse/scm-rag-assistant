from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.middleware.auth import get_current_user

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user=Depends(get_current_user),
):
    return current_user

@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
):

    try:

        user = AuthService.signup(
            db=db,
            name=request.name,
            email=request.email,
            password=request.password,
        )

        return user

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    try:

        user, token = AuthService.login(
            db=db,
            email=request.email,
            password=request.password,
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user,
        }

    except ValueError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )