from datetime import datetime, timezone

from app.core.errors import AuthenticationError
from app.core.config import settings
from app.core.security import create_token, decode_token, verify_password
from app.db.repositories.user_repository import UserRepository
from app.models.user import User
from app.schemas.auth import TokenPair, UserRead


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def authenticate(self, *, email: str, password: str) -> TokenPair:
        user = self.repository.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError()
        return self._issue_pair(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        claims = decode_token(refresh_token, expected_type="refresh")
        session = self.repository.get_refresh_session(str(claims["jti"]))
        if session is None or session.revoked_at is not None:
            raise AuthenticationError()
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise AuthenticationError()
        user = self.repository.get(int(str(claims["sub"])))
        if user is None or not user.is_active:
            raise AuthenticationError()
        self.repository.revoke_refresh_session(session)
        return self._issue_pair(user)

    def logout(self, refresh_token: str, *, user_id: int) -> None:
        claims = decode_token(refresh_token, expected_type="refresh")
        if str(claims["sub"]) != str(user_id):
            raise AuthenticationError()
        session = self.repository.get_refresh_session(str(claims["jti"]))
        if session is not None and session.revoked_at is None:
            self.repository.revoke_refresh_session(session)

    def _issue_pair(self, user: User) -> TokenPair:
        access, _, _ = create_token(user_id=user.id, role=user.role, token_type="access")
        refresh, jti, refresh_expires = create_token(
            user_id=user.id, role=user.role, token_type="refresh"
        )
        self.repository.create_refresh_session(jti=jti, user_id=user.id, expires_at=refresh_expires)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=60 * settings.access_token_minutes,
            user=UserRead.model_validate(user),
        )
