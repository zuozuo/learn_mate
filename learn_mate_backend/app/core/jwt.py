"""JWT authentication utilities."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    """JWT token payload data."""

    user_id: int
    email: str
    exp: datetime
    token_type: str = "access"  # access or refresh


class JWTManager:
    """Manages JWT token operations."""

    algorithm = "HS256"
    access_token_expire_minutes = 60  # 1 hour
    refresh_token_expire_days = 7  # 7 days

    @classmethod
    def create_access_token(cls, user_id: int, email: str) -> str:
        """Create an access token."""
        expire = datetime.utcnow() + timedelta(minutes=cls.access_token_expire_minutes)
        data = TokenData(user_id=user_id, email=email, exp=expire, token_type="access")
        return jwt.encode(data.model_dump(), settings.SECRET_KEY, algorithm=cls.algorithm)

    @classmethod
    def create_refresh_token(cls, user_id: int, email: str) -> str:
        """Create a refresh token."""
        expire = datetime.utcnow() + timedelta(days=cls.refresh_token_expire_days)
        data = TokenData(user_id=user_id, email=email, exp=expire, token_type="refresh")
        return jwt.encode(data.model_dump(), settings.SECRET_KEY, algorithm=cls.algorithm)

    @classmethod
    def verify_token(cls, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[cls.algorithm])
            return TokenData(**payload)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @classmethod
    def create_token_pair(cls, user_id: int, email: str) -> Dict[str, str]:
        """Create both access and refresh tokens."""
        return {
            "access_token": cls.create_access_token(user_id, email),
            "refresh_token": cls.create_refresh_token(user_id, email),
            "token_type": "bearer",
        }
