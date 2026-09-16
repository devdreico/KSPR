from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings
from .models import UserProfile

pwd_context = None  # Not using passlib anymore


class AuthError(Exception):
    pass


class InvalidCredentials(AuthError):
    pass


class TokenExpired(AuthError):
    pass


class UserNotFound(AuthError):
    pass


class JWTHandler:
    def __init__(self, settings: Settings):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expiration_minutes = settings.jwt_expiration_minutes

    def create_access_token(self, user_id: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self.expiration_minutes)
        to_encode = {"sub": user_id, "exp": expire, "iat": datetime.now(UTC)}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if not user_id:
                raise InvalidCredentials("Token inválido: sin subject")
            return user_id
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpired("Token expirado") from exc
        except jwt.PyJWTError as exc:
            raise InvalidCredentials(f"Token inválido: {exc}") from exc


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt directly."""
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


async def get_current_user(
    authorization: str = Header(default=None, alias="Authorization"),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserProfile:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación faltantes",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    jwt_handler = JWTHandler(settings)

    try:
        user_id = jwt_handler.decode_token(token)
    except TokenExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    from .repository import UserRepository

    user_repo = UserRepository(settings)
    user = await user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    authorization: str = Header(default=None, alias="Authorization"),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UserProfile | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        return await get_current_user(authorization, settings)
    except HTTPException:
        return None