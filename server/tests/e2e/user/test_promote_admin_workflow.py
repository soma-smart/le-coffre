"""
E2E Test for Promote Admin Workflow

Tests the complete lifecycle of promoting a user to admin role.
"""


def test_promote_admin_complete_workflow(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    Complete end-to-end workflow for promoting users to admin role.

    This comprehensive test covers:
    1. Creating a regular user (non-admin)
    2. Verifying user doesn't have admin role initially
    3. Successfully promoting user to admin
    4. Verifying user has admin role after promotion
    5. Attempting to promote already-admin user (should fail with 400)
    6. Non-admin attempting to promote another user (should fail with 403)
    7. Attempting to promote non-existent user (should fail with 404)
    8. Verifying promoted user can be retrieved with admin role
    """

    # ========== Step 1: Create regular user (non-admin) ==========
    regular_user = sso_user_factory("regular@example.com", "Regular User")
    regular_user_id = regular_user["user_id"]

    # ========== Step 2: Verify user doesn't have admin role initially ==========
    get_user_response = authenticated_admin_client.get(f"/api/users/{regular_user_id}")
    assert get_user_response.status_code == 200
    user_data = get_user_response.json()
    assert user_data["id"] == regular_user_id
    assert "admin" not in user_data.get("roles", []), (
        "User should not be admin initially"
    )

    # ========== Step 3: Admin successfully promotes user to admin ==========
    promote_response = authenticated_admin_client.post(
        f"/api/users/{regular_user_id}/promote-admin"
    )
    assert promote_response.status_code == 204, (
        f"Promotion should succeed, got {promote_response.status_code}: {promote_response.text}"
    )

    # ========== Step 4: Verify user now has admin role ==========
    get_promoted_user = authenticated_admin_client.get(f"/api/users/{regular_user_id}")
    assert get_promoted_user.status_code == 200
    promoted_user_data = get_promoted_user.json()
    assert "admin" in promoted_user_data.get("roles", []), (
        "User should have admin role after promotion"
    )

    # ========== Step 5: Attempt to promote already-admin user (should fail) ==========
    promote_again_response = authenticated_admin_client.post(
        f"/api/users/{regular_user_id}/promote-admin"
    )
    assert promote_again_response.status_code == 400, (
        "Promoting already-admin user should return 400"
    )
    error_detail = promote_again_response.json()["detail"].lower()
    assert "already" in error_detail or "admin" in error_detail, (
        "Error message should indicate user is already admin"
    )

    # ========== Step 6: Non-admin attempts to promote another user (should fail) ==========
    # Create two more users: one non-admin and one target
    non_admin_user = sso_user_factory("nonprivileged@example.com", "Non Admin")
    non_admin_client = non_admin_user["client"]

    target_user = sso_user_factory("target@example.com", "Target User")
    target_user_id = target_user["user_id"]

    unauthorized_promote = non_admin_client.post(
        f"/api/users/{target_user_id}/promote-admin"
    )
    assert unauthorized_promote.status_code == 403, (
        "Non-admin should not be able to promote users"
    )
    assert "admin" in unauthorized_promote.json()["detail"].lower(), (
        "Error message should mention admin requirement"
    )

    # ========== Step 7: Attempt to promote non-existent user (should fail) ==========
    fake_user_id = "00000000-0000-0000-0000-000000000000"

    promote_nonexistent = authenticated_admin_client.post(
        f"/api/users/{fake_user_id}/promote-admin"
    )
    assert promote_nonexistent.status_code == 404, (
        "Promoting non-existent user should return 404"
    )
    assert "not found" in promote_nonexistent.json()["detail"].lower(), (
        "Error message should indicate user not found"
    )

    # ========== Step 8: Verify promoted user data is accessible ==========
    final_check = authenticated_admin_client.get(f"/api/users/{regular_user_id}")
    assert final_check.status_code == 200
    final_user_data = final_check.json()
    assert final_user_data["username"] == "regular"
    assert final_user_data["email"] == "regular@example.com"
    assert "admin" in final_user_data["roles"]
