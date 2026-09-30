from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenPair, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenPair)
def login(request: LoginRequest, db: DatabaseSession) -> TokenPair:
    return AuthService(UserRepository(db)).authenticate(
        email=request.email, password=request.password
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(request: RefreshRequest, db: DatabaseSession) -> TokenPair:
    return AuthService(UserRepository(db)).refresh(request.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: LogoutRequest, db: DatabaseSession, _: CurrentUser) -> Response:
    AuthService(UserRepository(db)).logout(request.refresh_token, user_id=_.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
def current_user(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
