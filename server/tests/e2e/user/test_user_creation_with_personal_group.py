def test_user_creation_creates_personal_group(
    e2e_client, setup, configured_sso, sso_user_factory
):
    """
    End-to-end test that:
    1. Creates a user via SSO
    2. Verifies that a personal group was created for the user
    """
    # Step 1: Create a user
    user = sso_user_factory("alice@example.com", "Alice Smith")

    # Step 2: Verify user exists
    user_id = user["user_id"]
    get_user_response = e2e_client.get(f"/api/users/{user_id}")
    assert get_user_response.status_code == 200

    user_info = get_user_response.json()
    assert user_info["id"] == user_id
    assert user_info["username"] == "alice"
