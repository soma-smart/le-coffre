"""
E2E test for /users/me endpoint.
This test verifies the complete workflow of getting authenticated user information.
"""


def test_get_user_me_returns_current_user_info(authenticated_admin_client):
    """
    Test that authenticated user can get their own information via /users/me.

    Workflow:
    1. User is already authenticated (via fixture)
    2. Call GET /users/me
    3. Verify user information is returned
    """
    # Act: Get current user information
    response = authenticated_admin_client.get("/api/users/me")

    # Assert: Response is successful
    assert response.status_code == 200

    # Assert: Response contains expected user data
    user_data = response.json()
    assert "id" in user_data
    assert "username" in user_data
    assert "email" in user_data
    assert "name" in user_data
    assert "roles" in user_data

    # Assert: Email matches the admin email
    assert user_data["email"] == "admin@example.com"
    assert user_data["name"] == "System Administrator"


def test_get_user_me_without_authentication_fails(e2e_client):
    """
    Test that unauthenticated requests to /users/me fail with 401.

    Workflow:
    1. Call GET /users/me without authentication
    2. Verify request fails with 401 Unauthorized
    """
    # Act: Try to get user info without authentication
    response = e2e_client.get("/api/users/me")

    # Assert: Request fails with 401
    assert response.status_code == 401


def test_get_user_me_with_sso_user(e2e_client, sso_user_token):
    """
    Test that SSO authenticated user can get their own information.

    Workflow:
    1. User authenticates via SSO (via fixture)
    2. Call GET /users/me with SSO user token
    3. Verify SSO user information is returned
    """
    # Arrange: Set the SSO user's token in cookies
    e2e_client.cookies.set("access_token", sso_user_token["token"])

    # Act: Get current user information
    response = e2e_client.get("/api/users/me")

    # Assert: Response is successful
    assert response.status_code == 200

    # Assert: Response contains SSO user data
    user_data = response.json()
    assert user_data["email"] == sso_user_token["email"]
    assert user_data["name"] == sso_user_token["display_name"]
    assert user_data["id"] == sso_user_token["user_id"]
