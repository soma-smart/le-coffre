"""
Test cookie-based authentication flow.
This test verifies that JWT tokens are properly set in cookies
and can be used for authentication.
"""


def test_login_sets_cookie_and_returns_user_info(e2e_client):
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
    assert cookies.get("refresh_token") is not None
    assert len(cookies.get("refresh_token")) > 0


def test_authenticated_request_with_cookie(
    authenticated_admin_client, setup, admin_personal_group_id
):
    """
    Test that authenticated requests work with cookies.
    The authenticated_admin_client fixture already has cookies set.
    """
    # Try to create a password (requires authentication)
    password_data = {
        "name": "Cookie Test Entry",
        "password": "MyS3cur3P@ss!",
        "folder": "Cookie Tests",
        "group_id": admin_personal_group_id,
    }
    create_response = authenticated_admin_client.post(
        "/api/passwords/", json=password_data
    )

    assert create_response.status_code == 201


def test_authenticated_request_without_auth_fails(unauthenticated_client, setup):
    """Test that requests without authentication fail."""
    # Try to create a password (requires authentication)
    password_data = {
        "name": "Test Entry",
        "password": "MyS3cur3P@ss!",
        "folder": "Test",
    }

    create_response = unauthenticated_client.post("/api/passwords/", json=password_data)

    # Should fail because no authentication provided
    assert create_response.status_code == 401


def test_cookie_authentication_works(e2e_client):
    """
    Test that cookie authentication works correctly.
    This test only verifies cookies work for authentication,
    without involving the vault setup.
    """
    # Register and login to get cookies
    admin_data = {
        "email": "cookie_auth@example.com",
        "password": "password123",
        "display_name": "Cookie Auth Admin",
    }
    register_response = e2e_client.post("/api/auth/register-admin", json=admin_data)
    assert register_response.status_code == 201

    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "cookie_auth@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    # Verify that cookies are set by checking a protected endpoint
    # Use the /users/me endpoint which requires authentication
    me_response = e2e_client.get("/api/users/me")
    assert me_response.status_code == 200

    user_data = me_response.json()
    assert user_data["email"] == "cookie_auth@example.com"
    assert user_data["name"] == "Cookie Auth Admin"
    assert "admin" in user_data["roles"]


def test_request_without_cookie_fails(unauthenticated_client, setup):
    """
    Test that requests without cookies fail properly for protected endpoints.
    Uses a fresh client without cookies to ensure authentication is required.
    """
    password_data = {
        "name": "Test Password",
        "password": "MyS3cur3P@ss!",
        "folder": "Test",
    }

    # This should fail without authentication (protected endpoint)
    create_response = unauthenticated_client.post(
        "/api/passwords/",
        json=password_data,
    )

    assert create_response.status_code == 401
