"""Custom security implementations for API authentication."""

from typing import Optional
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class HTTPBearerWith401(HTTPBearer):
    """Custom HTTPBearer that returns 401 instead of 403 for missing credentials."""

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """Validate the authorization header and return credentials."""
        authorization = request.headers.get("Authorization")
        scheme, credentials = self.get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)

    def get_authorization_scheme_param(self, authorization_header_value: Optional[str]) -> tuple[str, str]:
        """Extract scheme and param from authorization header."""
        if not authorization_header_value:
            return "", ""
        scheme, _, param = authorization_header_value.partition(" ")
        return scheme, param
