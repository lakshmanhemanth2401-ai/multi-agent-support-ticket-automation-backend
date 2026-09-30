from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.errors import AuthenticationError, SecurityConfigurationError

_password_hash = PasswordHash.recommended()
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_token(*, user_id: int, role: str, token_type: str) -> tuple[str, str, datetime]:
    secret = settings.jwt_secret.get_secret_value()
    if len(secret) < 32:
        raise SecurityConfigurationError()
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    expires_at = now + lifetime
    jti = str(uuid4())
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "type": token_type,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        secret,
        algorithm=_ALGORITHM,
    )
    return token, jti, expires_at


def decode_token(token: str, *, expected_type: str) -> dict[str, object]:
    secret = settings.jwt_secret.get_secret_value()
    if len(secret) < 32:
        raise SecurityConfigurationError()
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "role", "type", "jti", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError() from exc
    if claims.get("type") != expected_type:
        raise AuthenticationError()
    return claims
