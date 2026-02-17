"""
E2E Test: Promoted Admin Can Promote Other Users

Tests that a user who has been promoted to admin can successfully promote other users,
verifying that promoted admins have the same rights as the original admin.
"""


def test_promoted_admin_can_promote_another_user(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    Complete workflow testing that a promoted admin can promote other users.

    This test verifies:
    1. Original admin can promote a regular user to admin
    2. The promoted admin (after token refresh) can promote another user
    3. The second promoted user successfully receives admin role
    4. Promoted admins have the same rights as the original admin

    Steps:
    - Create user1 via SSO (regular user)
    - Admin promotes user1 to admin
    - User1 refreshes token to get updated roles
    - Create user2 via SSO (regular user)
    - User1 promotes user2 to admin
    - Verify user2 has admin role
    """

    # ========== Step 1: Create user1 via SSO ==========
    user1 = sso_user_factory("user1@example.com", "User One")
    user1_id = user1["user_id"]
    user1_client = user1["client"]

    # Verify user1 is NOT admin initially
    get_user1_response = authenticated_admin_client.get(f"/api/users/{user1_id}")
    assert get_user1_response.status_code == 200
    user1_data = get_user1_response.json()
    assert "admin" not in user1_data.get("roles", []), (
        "User1 should not be admin initially"
    )

    # ========== Step 2: Admin promotes user1 to admin ==========
    promote_user1_response = authenticated_admin_client.post(
        f"/api/users/{user1_id}/promote-admin"
    )
    assert promote_user1_response.status_code == 204, (
        f"Admin should be able to promote user1, got {promote_user1_response.status_code}: {promote_user1_response.text}"
    )

    # Verify user1 has admin role in database
    get_promoted_user1 = authenticated_admin_client.get(f"/api/users/{user1_id}")
    assert get_promoted_user1.status_code == 200
    promoted_user1_data = get_promoted_user1.json()
    assert "admin" in promoted_user1_data.get("roles", []), (
        "User1 should have admin role after promotion"
    )

    # ========== Step 3: User1 refreshes token to get updated roles ==========
    refresh_response = user1_client.post("/api/auth/refresh-token")
    assert refresh_response.status_code == 200, (
        f"Token refresh should succeed, got {refresh_response.status_code}: {refresh_response.text}"
    )
    assert refresh_response.json()["message"] == "Access token refreshed successfully"

    # ========== Step 4: Verify user1 can access admin-only endpoints ==========
    # Try to get list of users (admin-only operation)
    users_list_response = user1_client.get("/api/users")
    assert users_list_response.status_code == 200, (
        f"Promoted admin (user1) should be able to list users, got {users_list_response.status_code}: {users_list_response.text}"
    )

    # ========== Step 5: Create user2 via SSO ==========
    user2 = sso_user_factory("user2@example.com", "User Two")
    user2_id = user2["user_id"]

    # Verify user2 is NOT admin initially
    get_user2_response = authenticated_admin_client.get(f"/api/users/{user2_id}")
    assert get_user2_response.status_code == 200
    user2_data = get_user2_response.json()
    assert "admin" not in user2_data.get("roles", []), (
        "User2 should not be admin initially"
    )

    # ========== Step 6: User1 (promoted admin) promotes user2 to admin ==========
    promote_user2_response = user1_client.post(f"/api/users/{user2_id}/promote-admin")
    assert promote_user2_response.status_code == 204, (
        f"Promoted admin (user1) should be able to promote user2, got {promote_user2_response.status_code}: {promote_user2_response.text}"
    )

    # ========== Step 7: Verify user2 has admin role ==========
    get_promoted_user2 = authenticated_admin_client.get(f"/api/users/{user2_id}")
    assert get_promoted_user2.status_code == 200
    promoted_user2_data = get_promoted_user2.json()
    assert "admin" in promoted_user2_data.get("roles", []), (
        "User2 should have admin role after being promoted by user1"
    )

    # ========== Step 8: Final verification - user2 can also perform admin actions ==========
    user2_client = user2["client"]

    # User2 refreshes token to get updated roles
    refresh_user2_response = user2_client.post("/api/auth/refresh-token")
    assert refresh_user2_response.status_code == 200, (
        f"User2 token refresh should succeed, got {refresh_user2_response.status_code}: {refresh_user2_response.text}"
    )

    # User2 should be able to list users (admin operation)
    users_list_by_user2 = user2_client.get("/api/users")
    assert users_list_by_user2.status_code == 200, (
        f"Promoted admin (user2) should be able to list users, got {users_list_by_user2.status_code}: {users_list_by_user2.text}"
    )
