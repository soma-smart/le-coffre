def test_create_user_complete_workflow(e2e_client, setup, client_factory):
    """
    Complete workflow: Create user → Verify user → Login as user → Verify session

    This tests the entire user creation lifecycle:
    1. Admin creates a new user
    2. Verify user was created with correct details
    3. Login as the new user to verify password works
    4. Verify new user can access their own data
    """
    # Step 1: Setup - Admin is authenticated via e2e_client and setup fixture
    # Get admin's personal group ID
    admin_me_response = e2e_client.get("/api/users/me")
    assert admin_me_response.status_code == 200
    admin_data = admin_me_response.json()
    print(f"Admin authenticated: {admin_data['email']}")

    # Step 2: CREATE - Admin creates a new user
    new_user_data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "name": "Test User",
        "password": "SecurePassword123!",
    }

    create_response = e2e_client.post("/api/users/", json=new_user_data)
    assert create_response.status_code == 201, (
        f"Failed to create user: {create_response.text}"
    )
    created_user = create_response.json()
    user_id = created_user["id"]
    print(f"User created with ID: {user_id}")

    # Step 3: READ - Admin verifies user was created with correct details
    get_user_response = e2e_client.get(f"/api/users/{user_id}")
    assert get_user_response.status_code == 200
    user_details = get_user_response.json()
    assert user_details["username"] == new_user_data["username"]
    assert user_details["email"] == new_user_data["email"]
    assert user_details["name"] == new_user_data["name"]
    assert "password" not in user_details, "Password should not be returned"
    print(f"User verified: {user_details['email']}")

    # Step 4: VERIFY AUTH - Login as the new user to verify password works
    # Create a separate client to avoid cookie interference
    new_user_client = client_factory()

    login_response = new_user_client.post(
        "/api/auth/login",
        json={
            "email": new_user_data["email"],
            "password": new_user_data["password"],
        },
    )
    assert login_response.status_code == 200, (
        f"Failed to login as new user: {login_response.text}"
    )
    print("New user successfully logged in")

    # Verify access token cookie was set
    access_token = login_response.cookies.get("access_token")
    assert access_token is not None, "access_token cookie should be set"

    # Step 5: VERIFY SESSION - New user can access their own data
    new_user_me_response = new_user_client.get("/api/users/me")
    assert new_user_me_response.status_code == 200
    new_user_me_data = new_user_me_response.json()
    assert new_user_me_data["email"] == new_user_data["email"]
    assert new_user_me_data["name"] == new_user_data["name"]
    assert new_user_me_data["id"] == user_id
    print(f"New user session verified: {new_user_me_data['email']}")

    # Step 6: Verify new user has a personal group (created by the use case)
    assert (
        "personal_group_id" in new_user_me_data
    ), "User should have a personal group"
    personal_group_id = new_user_me_data["personal_group_id"]
    print(f"Personal group created: {personal_group_id}")

    # Verify personal group exists and has correct properties
    get_group_response = new_user_client.get(f"/api/groups/{personal_group_id}")
    assert get_group_response.status_code == 200
    group_data = get_group_response.json()
    assert group_data["is_personal"] is True
    assert new_user_data["username"] in group_data["name"].lower()
    print(f"Personal group verified: {group_data['name']}")

    # Step 7: Verify admin can still access the created user
    admin_get_user_response = e2e_client.get(f"/api/users/{user_id}")
    assert admin_get_user_response.status_code == 200
    assert admin_get_user_response.json()["email"] == new_user_data["email"]
    print("Admin can still access created user")
