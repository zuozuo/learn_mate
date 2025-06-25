"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
and token verification.
"""

import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.logging import logger
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    SessionResponse,
)
from app.services.database import DatabaseService
from app.utils.auth import (
    create_access_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_string,
)

router = APIRouter()
security = HTTPBearer()
db_service = DatabaseService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get the current user ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        User: The user extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        token_value = verify_token(token)
        if token_value is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if token_value is a UUID (session ID) or numeric (user ID)
        try:
            # Try to parse as UUID first
            uuid.UUID(token_value)
            # It's a session ID, get user from session
            session = await db_service.get_session(token_value)
            if session is None:
                logger.error("session_not_found", session_id=token_value)
                raise HTTPException(
                    status_code=404,
                    detail="Session not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user = await db_service.get_user(session.user_id)
            if user is None:
                logger.error("user_not_found", user_id=session.user_id)
                raise HTTPException(
                    status_code=404,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user
        except ValueError:
            # Not a UUID, try as numeric user ID
            user_id_int = int(token_value)
            user = await db_service.get_user(user_id_int)
            if user is None:
                logger.error("user_not_found", user_id=user_id_int)
                raise HTTPException(
                    status_code=404,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user

    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """Get the current session ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        Session: The session extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        session_id = verify_token(token)
        if session_id is None:
            logger.error("session_id_not_found", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Sanitize session_id before using it
        session_id = sanitize_string(session_id)

        # Verify session exists in database
        session = await db_service.get_session(session_id)
        if session is None:
            logger.error("session_not_found", session_id=session_id)
            raise HTTPException(
                status_code=404,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return session
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("", response_model=SessionResponse)
async def create_session(user: User = Depends(get_current_user)):
    """Create a new chat session for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        SessionResponse: The session ID, name, and access token
    """
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create session in database
        session = await db_service.create_session(session_id, user.id)

        # Create access token for the session
        token = create_access_token(session_id)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
            expires_at=token.expires_at.isoformat(),
        )

        return SessionResponse(session_id=session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch("/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str, name: str = Form(...), current_session: Session = Depends(get_current_session)
):
    """Update a session's name.

    Args:
        session_id: The ID of the session to update
        name: The new name for the session
        current_session: The current session from auth

    Returns:
        SessionResponse: The updated session information
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # Update the session name
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        # Create a new token (not strictly necessary but maintains consistency)
        token = create_access_token(sanitized_session_id)

        return SessionResponse(session_id=sanitized_session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.error("session_update_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/{session_id}")
async def delete_session(session_id: str, current_session: Session = Depends(get_current_session)):
    """Delete a session for the authenticated user.

    Args:
        session_id: The ID of the session to delete
        current_session: The current session from auth

    Returns:
        None
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # Delete the session
        await db_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=current_session.user_id)
    except ValueError as ve:
        logger.error("session_deletion_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("", response_model=List[SessionResponse])
async def get_user_sessions(user: User = Depends(get_current_user)):
    """Get all session IDs for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        List[SessionResponse]: List of session IDs
    """
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
                token=create_access_token(session.id),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
