"""
Test cookie-based authentication flow.
This test verifies that JWT tokens are properly set in cookies
and can be used for authentication.
"""

from fastapi.testclient import TestClient
from main import app


def test_login_sets_cookies(e2e_client):
    """Test that login endpoint sets access_token and refresh_token cookies."""
    # Register an admin user
    admin_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "display_name": "Test Admin",
    }
    register_response = e2e_client.post("/api/auth/register-admin", json=admin_data)
    assert register_response.status_code == 201

    # Login
    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "securepassword123",
        },
    )

    assert login_response.status_code == 200

    # Verify cookies are set
    cookies = login_response.cookies
    assert "access_token" in cookies, "access_token cookie should be set"
    assert "refresh_token" in cookies, "refresh_token cookie should be set"

    # Verify cookie properties
    access_token_cookie = cookies.get("access_token")
    assert access_token_cookie is not None
    assert len(access_token_cookie) > 0


def test_authenticated_request_with_cookie(authenticated_admin_client, setup):
    """
    Test that authenticated requests work with cookies.
    The authenticated_admin_client fixture already has cookies set.
    """
    # Try to create a password (requires authentication)
    password_data = {
        "name": "Cookie Test Entry",
        "password": "MyS3cur3P@ss!",
        "folder": "Cookie Tests",
    }

    # No need to set Authorization header - cookies should work
    create_response = authenticated_admin_client.post(
        "/api/passwords/", json=password_data
    )

    assert create_response.status_code == 201
    created_password = create_response.json()
    assert created_password["name"] == "Cookie Test Entry"


def test_authenticated_request_without_auth_fails(e2e_client, setup):
    """Test that requests without authentication fail."""
    # Create a fresh client without cookies

    fresh_client = TestClient(app)

    # Try to create a password (requires authentication)
    password_data = {
        "name": "Test Entry",
        "password": "MyS3cur3P@ss!",
        "folder": "Test",
    }

    create_response = fresh_client.post("/api/passwords/", json=password_data)

    # Should fail because no authentication provided
    assert create_response.status_code == 401


def test_cookie_authentication_has_priority_over_header(e2e_client, setup):
    """
    Test that cookie authentication takes priority over header authentication.
    This ensures the new method is preferred.
    """
    # Register and login to get cookies
    admin_data = {
        "email": "cookie_priority@example.com",
        "password": "password123",
        "display_name": "Cookie Priority Admin",
    }
    e2e_client.post("/api/auth/register-admin", json=admin_data)

    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "cookie_priority@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    # Now the client has valid cookies
    # Try to make a request with an INVALID header (but valid cookie)
    password_data = {
        "name": "Priority Test Entry",
        "password": "MyS3cur3P@ss!",
        "folder": "Tests",
    }

    # This should succeed because the cookie is valid, even though the header is invalid
    create_response = e2e_client.post(
        "/api/passwords/",
        json=password_data,
        headers={"Authorization": "Bearer invalid_token_should_be_ignored"},
    )

    # Should succeed because cookie takes priority
    assert create_response.status_code == 201


def test_header_authentication_still_works_for_backward_compatibility(
    admin_token, setup
):
    """
    Test that header-based authentication still works for backward compatibility.
    This is important for existing tests and clients that don't use cookies.
    Uses a fresh client without cookies to ensure we're testing header-only auth.
    """
    # Use a fresh client without cookies to test header-only authentication
    fresh_client = TestClient(app)

    user_data = {
        "username": "headeruser",
        "email": "headeruser@example.com",
        "name": "Header User",
    }

    # Use old-style header authentication without cookies
    create_response = fresh_client.post(
        "/api/users/",
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["email"] == "headeruser@example.com"
