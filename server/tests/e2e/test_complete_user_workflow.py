"""
Complete End-to-End User Workflow.

This test covers the entire user management system in one comprehensive workflow:
1. Authentication checks (login with wrong/correct password, response fields)
2. User creation (admin creates local user, verifies session and personal group)
3. SSO user personal group creation
4. Group deletion (lifecycle + edge cases: personal group, group with passwords)
5. Admin promotion (promote, idempotency, authorization, non-existent user)
6. Promoted admin can promote others (chain promotion, token refresh, admin actions)
7. User deletion (auth guards: no cookie, invalid cookie, valid admin)
8. Password update (new password, old invalidated, successive updates)
"""


def test_complete_user_workflow(
    authenticated_admin_client,
    sso_user_factory,
    client_factory,
    unauthenticated_client,
):
    """
    Complete user management workflow covering all user features step by step.

    Uses authenticated_admin_client (admin@example.com / password="admin") and
    sso_user_factory (which brings in configured_sso + setup).
    """

    # =========================================================================
    # PHASE 1: LOGIN AUTHENTICATION CHECKS
    # =========================================================================

    # Step 1.1: Login with wrong password must fail
    wrong_login_response = authenticated_admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "wrong_password"},
    )
    assert wrong_login_response.status_code == 401

    # Step 1.2: Login with correct password returns expected response fields
    correct_login_response = authenticated_admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin"},
    )
    assert correct_login_response.status_code == 200
    login_result = correct_login_response.json()
    assert login_result["email"] == "admin@example.com"
    assert login_result["message"] == "Login successful"

    jwt_token = correct_login_response.cookies.get("access_token")
    assert jwt_token is not None

    # =========================================================================
    # PHASE 2: USER CREATION (admin creates a local user)
    # =========================================================================

    # Step 2.1: Admin creates a new local user
    new_user_data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "name": "Test User",
        "password": "SecurePassword123!",
    }
    create_response = authenticated_admin_client.post("/api/users/", json=new_user_data)
    assert create_response.status_code == 201, f"Failed to create user: {create_response.text}"
    created_user = create_response.json()
    created_user_id = created_user["id"]

    # Step 2.2: Admin verifies user was created with correct details
    get_user_response = authenticated_admin_client.get(f"/api/users/{created_user_id}")
    assert get_user_response.status_code == 200
    user_details = get_user_response.json()
    assert user_details["username"] == new_user_data["username"]
    assert user_details["email"] == new_user_data["email"]
    assert user_details["name"] == new_user_data["name"]
    assert "password" not in user_details, "Password should not be returned"

    # Step 2.3: Login as the new user to verify password works
    new_user_client = client_factory()
    login_response = new_user_client.post(
        "/api/auth/login",
        json={"email": new_user_data["email"], "password": new_user_data["password"]},
    )
    assert login_response.status_code == 200, f"Failed to login as new user: {login_response.text}"
    assert login_response.cookies.get("access_token") is not None

    # Step 2.4: New user can access their own session data
    new_user_me_response = new_user_client.get("/api/users/me")
    assert new_user_me_response.status_code == 200
    new_user_me_data = new_user_me_response.json()
    assert new_user_me_data["email"] == new_user_data["email"]
    assert new_user_me_data["name"] == new_user_data["name"]
    assert new_user_me_data["id"] == created_user_id

    # Step 2.5: New user has a personal group with correct properties
    assert "personal_group_id" in new_user_me_data, "User should have a personal group"
    personal_group_id = new_user_me_data["personal_group_id"]
    get_group_response = new_user_client.get(f"/api/groups/{personal_group_id}")
    assert get_group_response.status_code == 200
    group_data = get_group_response.json()
    assert group_data["is_personal"] is True
    assert new_user_data["username"] in group_data["name"].lower()

    # Step 2.6: Admin can still access the created user
    admin_get_user_response = authenticated_admin_client.get(f"/api/users/{created_user_id}")
    assert admin_get_user_response.status_code == 200
    assert admin_get_user_response.json()["email"] == new_user_data["email"]

    # =========================================================================
    # PHASE 3: SSO USER PERSONAL GROUP CREATION
    # =========================================================================

    # Step 3.1: Create SSO user and verify personal group is created
    alice = sso_user_factory("alice@example.com", "Alice Smith")
    alice_id = alice["user_id"]

    get_alice_response = authenticated_admin_client.get(f"/api/users/{alice_id}")
    assert get_alice_response.status_code == 200
    alice_info = get_alice_response.json()
    assert alice_info["id"] == alice_id
    assert alice_info["username"] == "alice"

    # =========================================================================
    # PHASE 4: GROUP DELETION
    # =========================================================================

    admin_me_response = authenticated_admin_client.get("/api/users/me")
    assert admin_me_response.status_code == 200
    admin_personal_group_id = admin_me_response.json()["personal_group_id"]

    # Step 4.1: Create a group
    create_group_response = authenticated_admin_client.post("/api/groups/", json={"name": "Test Group to Delete"})
    assert create_group_response.status_code == 201
    deletable_group_id = create_group_response.json()["id"]
    assert create_group_response.json()["name"] == "Test Group to Delete"

    # Step 4.2: Verify group exists
    get_group_response = authenticated_admin_client.get(f"/api/groups/{deletable_group_id}")
    assert get_group_response.status_code == 200
    assert get_group_response.json()["name"] == "Test Group to Delete"

    # Step 4.3: Delete the group
    delete_response = authenticated_admin_client.delete(f"/api/groups/{deletable_group_id}")
    assert delete_response.status_code == 204

    # Step 4.4: Verify group no longer exists
    get_deleted_response = authenticated_admin_client.get(f"/api/groups/{deletable_group_id}")
    assert get_deleted_response.status_code == 404

    # Step 4.5: Cannot delete personal group
    delete_personal_response = authenticated_admin_client.delete(f"/api/groups/{admin_personal_group_id}")
    assert delete_personal_response.status_code == 400
    assert "personal group" in delete_personal_response.json()["detail"].lower()

    # Step 4.6: Cannot delete group that still has passwords
    create_group2_response = authenticated_admin_client.post("/api/groups/", json={"name": "Group with Passwords"})
    assert create_group2_response.status_code == 201
    group_with_passwords_id = create_group2_response.json()["id"]

    create_password_response = authenticated_admin_client.post(
        "/api/passwords/",
        json={
            "name": "Test Password",
            "password": "SecureP@ss123",
            "folder": "default",
            "group_id": group_with_passwords_id,
        },
    )
    assert create_password_response.status_code == 201

    delete_group_with_passwords_response = authenticated_admin_client.delete(f"/api/groups/{group_with_passwords_id}")
    assert delete_group_with_passwords_response.status_code == 400
    assert (
        "still in use" in delete_group_with_passwords_response.json()["detail"].lower()
        or "still used" in delete_group_with_passwords_response.json()["detail"].lower()
    )

    # Step 4.7: Delete the password first, then the group succeeds
    password_id = create_password_response.json()["id"]
    delete_password_response = authenticated_admin_client.delete(f"/api/passwords/{password_id}")
    assert delete_password_response.status_code == 204

    delete_group_after_cleanup_response = authenticated_admin_client.delete(f"/api/groups/{group_with_passwords_id}")
    assert delete_group_after_cleanup_response.status_code == 204

    # =========================================================================
    # PHASE 5: ADMIN PROMOTION
    # =========================================================================

    # Step 5.1: Create a regular SSO user
    regular_user = sso_user_factory("regular@example.com", "Regular User")
    regular_user_id = regular_user["user_id"]

    # Step 5.2: Verify user has no admin role initially
    get_user_response = authenticated_admin_client.get(f"/api/users/{regular_user_id}")
    assert get_user_response.status_code == 200
    user_data = get_user_response.json()
    assert user_data["id"] == regular_user_id
    assert "admin" not in user_data.get("roles", [])

    # Step 5.3: Admin promotes user to admin
    promote_response = authenticated_admin_client.post(f"/api/users/{regular_user_id}/promote-admin")
    assert promote_response.status_code == 204, f"Promotion should succeed: {promote_response.text}"

    # Step 5.4: Verify user now has admin role
    get_promoted_user = authenticated_admin_client.get(f"/api/users/{regular_user_id}")
    assert get_promoted_user.status_code == 200
    promoted_user_data = get_promoted_user.json()
    assert "admin" in promoted_user_data.get("roles", [])

    # Step 5.5: Promote already-admin user returns 400
    promote_again_response = authenticated_admin_client.post(f"/api/users/{regular_user_id}/promote-admin")
    assert promote_again_response.status_code == 400
    error_detail = promote_again_response.json()["detail"].lower()
    assert "already" in error_detail or "admin" in error_detail

    # Step 5.6: Non-admin cannot promote users (403)
    non_admin_user = sso_user_factory("nonprivileged@example.com", "Non Admin")
    non_admin_client = non_admin_user["client"]

    target_user = sso_user_factory("target@example.com", "Target User")
    target_user_id = target_user["user_id"]

    unauthorized_promote = non_admin_client.post(f"/api/users/{target_user_id}/promote-admin")
    assert unauthorized_promote.status_code == 403
    assert "admin" in unauthorized_promote.json()["detail"].lower()

    # Step 5.7: Promoting non-existent user returns 404
    promote_nonexistent = authenticated_admin_client.post(
        "/api/users/00000000-0000-0000-0000-000000000000/promote-admin"
    )
    assert promote_nonexistent.status_code == 404
    assert "not found" in promote_nonexistent.json()["detail"].lower()

    # Step 5.8: Final verification of promoted user data
    final_check = authenticated_admin_client.get(f"/api/users/{regular_user_id}")
    assert final_check.status_code == 200
    final_user_data = final_check.json()
    assert final_user_data["username"] == "regular"
    assert final_user_data["email"] == "regular@example.com"
    assert "admin" in final_user_data["roles"]

    # =========================================================================
    # PHASE 6: PROMOTED ADMIN CAN PROMOTE OTHERS
    # =========================================================================

    # Step 6.1: Create user1 via SSO, verify not admin
    user1 = sso_user_factory("user1@example.com", "User One")
    user1_id = user1["user_id"]
    user1_client = user1["client"]

    get_user1_response = authenticated_admin_client.get(f"/api/users/{user1_id}")
    assert get_user1_response.status_code == 200
    assert "admin" not in get_user1_response.json().get("roles", [])

    # Step 6.2: Admin promotes user1 to admin
    promote_user1_response = authenticated_admin_client.post(f"/api/users/{user1_id}/promote-admin")
    assert promote_user1_response.status_code == 204, f"Admin should promote user1: {promote_user1_response.text}"

    # Step 6.3: Verify user1 has admin role in database
    get_promoted_user1 = authenticated_admin_client.get(f"/api/users/{user1_id}")
    assert get_promoted_user1.status_code == 200
    assert "admin" in get_promoted_user1.json().get("roles", [])

    # Step 6.4: User1 refreshes token to get updated roles
    refresh_response = user1_client.post("/api/auth/refresh-token")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["message"] == "Access token refreshed successfully"

    # Step 6.5: User1 can now access admin-only endpoints (list users)
    users_list_response = user1_client.get("/api/users")
    assert users_list_response.status_code == 200, (
        f"Promoted admin (user1) should list users: {users_list_response.text}"
    )

    # Step 6.6: Create user2, verify not admin
    user2 = sso_user_factory("user2@example.com", "User Two")
    user2_id = user2["user_id"]
    user2_client = user2["client"]

    get_user2_response = authenticated_admin_client.get(f"/api/users/{user2_id}")
    assert get_user2_response.status_code == 200
    assert "admin" not in get_user2_response.json().get("roles", [])

    # Step 6.7: User1 (promoted admin) promotes user2 to admin
    promote_user2_response = user1_client.post(f"/api/users/{user2_id}/promote-admin")
    assert promote_user2_response.status_code == 204, (
        f"Promoted admin (user1) should promote user2: {promote_user2_response.text}"
    )

    # Step 6.8: Verify user2 has admin role
    get_promoted_user2 = authenticated_admin_client.get(f"/api/users/{user2_id}")
    assert get_promoted_user2.status_code == 200
    assert "admin" in get_promoted_user2.json().get("roles", [])

    # Step 6.9: User2 refreshes token to get updated roles
    refresh_user2_response = user2_client.post("/api/auth/refresh-token")
    assert refresh_user2_response.status_code == 200

    # Step 6.10: User2 can also perform admin actions (list users)
    users_list_by_user2 = user2_client.get("/api/users")
    assert users_list_by_user2.status_code == 200, (
        f"Promoted admin (user2) should list users: {users_list_by_user2.text}"
    )

    # =========================================================================
    # PHASE 7: USER DELETION (auth guards)
    # =========================================================================

    # Step 7.1: Create SSO user to be deleted
    sso_user_to_delete = sso_user_factory("delete_me@example.com", "Delete Me")
    delete_target_id = sso_user_to_delete["user_id"]

    # Step 7.2: Verify user exists
    assert authenticated_admin_client.get(f"/api/users/{delete_target_id}").status_code == 200

    # Step 7.3: Delete without any authentication must return 401
    unauthenticated_client.disable_auto_csrf()
    delete_no_auth_response = unauthenticated_client.delete(f"/api/users/{delete_target_id}")
    assert delete_no_auth_response.status_code == 401

    # Step 7.4: Delete with invalid cookie (CSRF disabled) must return 403
    unauthenticated_client.cookies.set("access_token", "invalid_token")
    delete_invalid_response = unauthenticated_client.delete(f"/api/users/{delete_target_id}")
    assert delete_invalid_response.status_code == 403
    unauthenticated_client.enable_auto_csrf()

    # Step 7.5: Delete with valid admin credentials succeeds
    delete_valid_response = authenticated_admin_client.delete(f"/api/users/{delete_target_id}")
    assert delete_valid_response.status_code == 204

    # Step 7.6: Verify user is actually deleted
    get_deleted_user_response = authenticated_admin_client.get(f"/api/users/{delete_target_id}")
    assert get_deleted_user_response.status_code == 404

    # =========================================================================
    # PHASE 8: PASSWORD UPDATE
    # =========================================================================

    # Step 8.1: Get admin's current info
    admin_me_response2 = authenticated_admin_client.get("/api/users/me")
    assert admin_me_response2.status_code == 200
    admin_email = admin_me_response2.json()["email"]
    admin_id = admin_me_response2.json()["id"]

    old_password = "admin"
    new_password = "NewSecurePassword123!"

    # Step 8.2: Admin updates their own password
    update_response = authenticated_admin_client.put(
        "/api/users/me/password",
        json={"old_password": old_password, "new_password": new_password},
    )
    assert update_response.status_code == 204, f"Failed to update password: {update_response.text}"

    # Step 8.3: Updating with the now-wrong old password returns 401
    wrong_old_response = authenticated_admin_client.put(
        "/api/users/me/password",
        json={"old_password": old_password, "new_password": "AnotherPassword456!"},
    )
    assert wrong_old_response.status_code == 401

    # Step 8.4: Login with old password in a fresh client returns 401
    fresh_client = client_factory()
    old_password_login = fresh_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": old_password},
    )
    assert old_password_login.status_code == 401

    # Step 8.5: Login with new password succeeds
    new_password_login = fresh_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": new_password},
    )
    assert new_password_login.status_code == 200, f"Login with new password failed: {new_password_login.text}"
    assert new_password_login.cookies.get("access_token") is not None

    # Step 8.6: New session can access user data
    new_session_me = fresh_client.get("/api/users/me")
    assert new_session_me.status_code == 200
    new_session_data = new_session_me.json()
    assert new_session_data["email"] == admin_email
    assert new_session_data["id"] == admin_id

    # Step 8.7: Can update password again
    another_new_password = "YetAnotherPassword789!"
    update_again_response = fresh_client.put(
        "/api/users/me/password",
        json={"old_password": new_password, "new_password": another_new_password},
    )
    assert update_again_response.status_code == 204

    # Step 8.8: Login with latest password succeeds
    final_client = client_factory()
    final_login_response = final_client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": another_new_password},
    )
    assert final_login_response.status_code == 200

    # Step 8.9: Final session verification
    final_me_response = final_client.get("/api/users/me")
    assert final_me_response.status_code == 200
    assert final_me_response.json()["email"] == admin_email
