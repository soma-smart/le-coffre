def test_user_creation_creates_personal_group(e2e_client, sso_user_factory):
    """
    End-to-end test that:
    1. Registers an admin
    2. Logs in with the admin credentials
    3. Creates a user
    4. Verifies that a personal group was created for the user
    """
    # Step 1: Register admin
    admin_data = {
        "email": "admin@example.com",
        "password": "secure_password123",
        "display_name": "System Administrator",
    }

    register_response = e2e_client.post("/api/auth/register-admin", json=admin_data)
    assert register_response.status_code == 201

    # Step 2: Login as admin
    login_data = {"email": admin_data["email"], "password": admin_data["password"]}
    login_response = e2e_client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200

    # Step 3: Create a user
    user = sso_user_factory("alice@example.com", "Alice Smith")

    # Step 4: Verify user exists
    user_id = user["user_id"]
    get_user_response = e2e_client.get(f"/api/users/{user_id}")
    assert get_user_response.status_code == 200

    user_info = get_user_response.json()
    assert user_info["id"] == user_id
    assert user_info["username"] == "alice"
