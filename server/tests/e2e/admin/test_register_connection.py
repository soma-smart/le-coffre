from fastapi.testclient import TestClient
from main import app


def test_complete_admin_authentication_flow(e2e_client):
    """
    End-to-end test that:
    1. Registers an admin
    2. Logs in with the admin credentials
    3. Creates a random user
    4. Tries to delete the user without token (should fail)
    5. Tries to delete the user with invalid token (should fail)
    6. Deletes the user with valid admin token (should succeed)
    """
    admin_data = {
        "email": "admin@example.com",
        "password": "secure_password123",
        "display_name": "System Administrator",
    }

    # Step 1: Register admin
    register_response = e2e_client.post("/api/auth/register-admin", json=admin_data)

    assert register_response.status_code == 201
    register_data = register_response.json()

    assert register_data["email"] == admin_data["email"]
    assert register_data["display_name"] == admin_data["display_name"]
    assert register_data["message"] == "Admin registered successfully"

    # Step 2: Try login with wrong password
    login_data = {"email": admin_data["email"], "password": "wrong_password"}

    login_response = e2e_client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 401

    # Step 3: Login with correct password
    login_data = {"email": admin_data["email"], "password": admin_data["password"]}

    login_response = e2e_client.post("/api/auth/login", json=login_data)

    assert login_response.status_code == 200
    login_result = login_response.json()

    assert login_result["email"] == admin_data["email"]
    assert login_result["message"] == "Login successful"

    # Extract JWT token from cookie
    jwt_token = login_response.cookies.get("access_token")
    assert jwt_token is not None

    # Step 4: Create a random user to delete later
    user_data = {
        "username": "testuser_1234",
        "email": "test_1234@example.com",
        "name": "Test User",
    }

    create_user_response = e2e_client.post("/api/users/", json=user_data)
    assert create_user_response.status_code == 201
    created_user = create_user_response.json()
    user_id = created_user["id"]

    # Step 5: Check that the user exists
    assert e2e_client.get(f"/api/users/{user_id}").status_code == 200

    # Step 6: Try to delete user without authorization (no header, no cookie) - should fail
    # Create a fresh client without cookies to test unauthorized access
    fresh_client = TestClient(app)
    delete_response_no_auth = fresh_client.delete(f"/api/users/{user_id}")
    assert delete_response_no_auth.status_code == 401  # Changed from 422 to 401

    # Step 7: Try to delete user with invalid token (should fail)
    # Use fresh client to test that invalid header token fails
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    delete_response_invalid = fresh_client.delete(
        f"/api/users/{user_id}", headers=invalid_headers
    )
    assert delete_response_invalid.status_code == 401

    # Step 8: Delete user with valid admin token (should succeed)
    valid_headers = {"Authorization": f"Bearer {jwt_token}"}
    delete_response_valid = e2e_client.delete(
        f"/api/users/{user_id}", headers=valid_headers
    )
    assert delete_response_valid.status_code == 204

    # Step 9: Verify user is actually deleted by trying to get it
    get_response = e2e_client.get(f"/api/users/{user_id}")
    assert get_response.status_code == 404
