from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import RefreshSession, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def create(self, *, email: str, password_hash: str, role: str) -> User:
        user = User(email=email.lower(), password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_refresh_session(
        self, *, jti: str, user_id: int, expires_at: datetime
    ) -> RefreshSession:
        session = RefreshSession(jti=jti, user_id=user_id, expires_at=expires_at)
        self.db.add(session)
        self.db.commit()
        return session

    def get_refresh_session(self, jti: str) -> RefreshSession | None:
        return self.db.get(RefreshSession, jti)

    def revoke_refresh_session(self, session: RefreshSession) -> None:
        session.revoked_at = datetime.now(timezone.utc)
        self.db.add(session)
        self.db.commit()
