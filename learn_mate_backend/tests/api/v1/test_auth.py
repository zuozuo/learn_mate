"""Tests for authentication API endpoints."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User
from app.utils.auth import create_access_token, verify_token
from app.services.database import database_service


class TestAuthAPI:
    """Test suite for authentication endpoints."""
    
    @patch.object(database_service, 'get_user_by_email', new_callable=AsyncMock)
    @patch.object(database_service, 'create_user', new_callable=AsyncMock)
    def test_register_success(self, mock_create_user, mock_get_user_by_email, client: TestClient):
        """Test successful user registration."""
        # Mock that user doesn't exist
        mock_get_user_by_email.return_value = None
        
        # Mock successful user creation
        mock_user = User(id=1, email="newuser@example.com", hashed_password="hashed")
        mock_create_user.return_value = mock_user
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["email"] == "newuser@example.com"
        assert "token" in data
        assert "access_token" in data["token"]
        assert data["token"]["token_type"] == "bearer"
        assert "expires_at" in data["token"]
    
    @patch.object(database_service, 'get_user_by_email', new_callable=AsyncMock)
    def test_register_duplicate_email(
        self, 
        mock_get_user_by_email,
        client: TestClient, 
        test_user: User
    ):
        """Test registration with existing email."""
        # Mock that user already exists
        mock_get_user_by_email.return_value = test_user
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "AnotherPass123!"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak"
            }
        )
        
        assert response.status_code == 422
    
    @patch.object(database_service, 'get_user_by_email', new_callable=AsyncMock)
    def test_login_success(
        self,
        mock_get_user_by_email,
        client: TestClient,
        test_user: User
    ):
        """Test successful login."""
        # Mock successful user lookup
        mock_get_user_by_email.return_value = test_user
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
                "grant_type": "password"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify token is valid
        user_id = verify_token(data["access_token"])
        assert user_id == str(test_user.id)
    
    @patch.object(database_service, 'get_user_by_email', new_callable=AsyncMock)
    def test_login_wrong_password(
        self,
        mock_get_user_by_email,
        client: TestClient,
        test_user: User
    ):
        """Test login with wrong password."""
        # Mock user lookup - password verification will fail
        mock_get_user_by_email.return_value = test_user
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
                "grant_type": "password"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    @patch.object(database_service, 'get_user_by_email', new_callable=AsyncMock)
    def test_login_nonexistent_user(self, mock_get_user_by_email, client: TestClient):
        """Test login with non-existent user."""
        # Mock that user doesn't exist
        mock_get_user_by_email.return_value = None
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123",
                "grant_type": "password"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_invalid_grant_type(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test login with invalid grant type."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
                "grant_type": "client_credentials"
            }
        )
        
        assert response.status_code == 400
        assert "Unsupported grant type" in response.json()["detail"]
    
    @patch.object(database_service, 'get_user', new_callable=AsyncMock)
    def test_protected_endpoint_with_valid_token(
        self,
        mock_get_user,
        client: TestClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test accessing protected endpoint with valid token."""
        # Mock user lookup for token validation
        mock_get_user.return_value = test_user
        
        response = client.get(
            "/api/v1/conversations",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_protected_endpoint_without_token(
        self,
        client: TestClient
    ):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/conversations")
        
        assert response.status_code == 403
    
    @patch.object(database_service, 'get_user', new_callable=AsyncMock)
    def test_protected_endpoint_with_invalid_token(
        self,
        mock_get_user,
        client: TestClient
    ):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.get(
            "/api/v1/conversations",
            headers=headers
        )
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_expired_token(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test accessing protected endpoint with expired token."""
        # Create token with negative expiry (already expired)
        import os
        from datetime import datetime, timedelta
        import jwt
        
        payload = {
            "sub": str(test_user.id),
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        
        expired_token = jwt.encode(
            payload,
            os.getenv("JWT_SECRET_KEY", "test_secret"),
            algorithm="HS256"
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get(
            "/api/v1/conversations",
            headers=headers
        )
        
        assert response.status_code == 401
    
    def test_token_validation(self, test_user: User):
        """Test token creation and validation."""
        # Create token
        token = create_access_token(str(test_user.id))
        
        assert token.access_token is not None
        assert token.expires_at is not None
        
        # Verify token
        user_id = verify_token(token.access_token)
        assert user_id == str(test_user.id)
        
        # Test invalid token
        invalid_user_id = verify_token("invalid_token")
        assert invalid_user_id is None
    
    @patch.object(database_service, 'get_user', new_callable=AsyncMock)
    def test_get_current_user(
        self,
        mock_get_user,
        client: TestClient,
        session: Session,
        test_user: User
    ):
        """Test get_current_user dependency."""
        from app.api.v1.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create valid credentials
        token = create_access_token(str(test_user.id))
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token.access_token
        )
        
        # Mock database service
        mock_get_user.return_value = test_user
        
        # Test get_current_user
        user = asyncio.run(get_current_user(credentials))
        
        assert user.id == test_user.id
        assert user.email == test_user.email