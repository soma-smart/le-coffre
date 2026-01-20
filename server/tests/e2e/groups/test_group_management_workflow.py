"""
End-to-end tests for group management workflow.

This test module covers the complete workflow:
1. Create a group
2. Add members to the group
3. Remove members from the group
4. Verify authorization rules
"""


def test_group_management_complete_workflow(
    authenticated_admin_client, sso_user_factory
):
    """
    End-to-end test that:
    1. Creates two additional SSO users (to be members)
    2. Creates a group
    3. Adds a user to the group
    4. Verifies non-owner cannot add members
    5. Removes a user from the group
    6. Verifies non-owner cannot remove members
    7. Verifies cannot remove owner
    """
    # Step 1: Create two additional SSO users
    user1 = sso_user_factory("user1@example.com", "User One")
    user1_id = user1["user_id"]

    user2 = sso_user_factory("user2@example.com", "User Two")
    user2_id = user2["user_id"]

    # Step 2: Create a group (admin is owner)
    group_data = {"name": "Engineering Team"}
    create_group_response = authenticated_admin_client.post(
        "/api/groups/", json=group_data
    )
    assert create_group_response.status_code == 201

    group = create_group_response.json()
    assert group["name"] == "Engineering Team"
    assert "id" in group
    assert group["message"] == "Group created successfully"
    group_id = group["id"]

    # Step 3: Add user1 to the group
    add_member_data = {"user_id": user1_id}
    add_member_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_member_data
    )
    assert add_member_response.status_code == 201

    add_member_result = add_member_response.json()
    assert add_member_result["group_id"] == group_id
    assert add_member_result["user_id"] == user1_id
    assert add_member_result["message"] == "Member added successfully"

    # Step 4: Add user2 to the group
    add_member2_data = {"user_id": user2_id}
    add_member2_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_member2_data
    )
    assert add_member2_response.status_code == 201

    # Step 5: Verify idempotency - adding user1 again should succeed
    add_member_again_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_member_data
    )
    assert add_member_again_response.status_code == 201

    # Step 6: Remove user2 from the group
    remove_member_response = authenticated_admin_client.delete(
        f"/api/groups/{group_id}/members/{user2_id}"
    )
    assert remove_member_response.status_code == 200, remove_member_response.text

    remove_result = remove_member_response.json()
    assert remove_result["message"] == "Member removed successfully"

    # Step 7: Verify cannot remove user that is not a member
    remove_nonmember_response = authenticated_admin_client.delete(
        f"/api/groups/{group_id}/members/{user2_id}"
    )
    assert remove_nonmember_response.status_code == 400
    assert "is not a member of group" in remove_nonmember_response.json()["detail"]


def test_group_management_authorization_rules(
    e2e_client, sso_user_factory, client_factory
):
    """
    End-to-end test verifying authorization rules:
    1. Only owners can add members
    2. Only owners can remove members
    3. Cannot remove owners from groups

    Note: Using admin for group creation and SSO users as members/non-owners.
    """
    # Register admin (group owner)
    owner_data = {
        "email": "owner@example.com",
        "password": "owner_password",
        "display_name": "Group Owner",
    }
    e2e_client.post("/api/auth/register-admin", json=owner_data)
    e2e_client.post(
        "/api/auth/login",
        json={"email": owner_data["email"], "password": owner_data["password"]},
    )

    # Get owner user ID
    me_response = e2e_client.get("/api/users/me")
    owner_id = me_response.json()["id"]

    # Create SSO users (target for group membership and non-owner)
    target_user = sso_user_factory("target@example.com", "Target User")
    target_id = target_user["user_id"]

    non_owner_user = sso_user_factory("nonowner@example.com", "Non-Owner User")
    non_owner_user_id = non_owner_user["user_id"]

    # Owner creates a group
    group_response = e2e_client.post("/api/groups/", json={"name": "Test Group"})
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Add target to group as member
    add_response = e2e_client.post(
        f"/api/groups/{group_id}/members",
        json={"user_id": target_id},
    )

    assert add_response.status_code == 201

    # Create a new client for the non-owner user to avoid cookie conflicts
    non_owner_client = client_factory()
    non_owner_client.cookies.set("access_token", non_owner_user["token"])

    # Try to add the non-owner user to the group (as non-owner) - should fail with 403
    add_response = non_owner_client.post(
        f"/api/groups/{group_id}/members",
        json={"user_id": non_owner_user_id},
    )
    assert add_response.status_code == 403
    assert "is not an owner of group" in add_response.json()["detail"]

    # Try to remove user as non-owner - should fail with 403
    remove_response = non_owner_client.delete(
        f"/api/groups/{group_id}/members/{target_id}"
    )
    assert remove_response.status_code == 403
    assert "is not an owner of group" in remove_response.json()["detail"]

    # Try to remove owner - should fail with 400
    remove_owner_response = e2e_client.delete(
        f"/api/groups/{group_id}/members/{owner_id}"
    )
    assert remove_owner_response.status_code == 400
    assert "Cannot remove owner" in remove_owner_response.json()["detail"]


def test_group_creation_requires_authentication(e2e_client):
    """
    Test that group operations require authentication.
    """
    # Try to create group without authentication
    group_data = {"name": "Unauthorized Group"}
    response = e2e_client.post("/api/groups/", json=group_data)
    assert response.status_code == 401  # Unauthorized


def test_cannot_add_nonexistent_user_to_group(e2e_client):
    """
    Test that adding a non-existent user to a group fails properly.
    """
    # Register and login
    admin_data = {
        "email": "admin@example.com",
        "password": "password",
        "display_name": "Admin",
    }
    e2e_client.post("/api/auth/register-admin", json=admin_data)
    e2e_client.post(
        "/api/auth/login",
        json={"email": admin_data["email"], "password": admin_data["password"]},
    )

    # Create group
    group_response = e2e_client.post("/api/groups/", json={"name": "Test Group"})
    group_id = group_response.json()["id"]

    # Try to add non-existent user
    fake_user_id = "00000000-0000-0000-0000-000000000000"
    add_response = e2e_client.post(
        f"/api/groups/{group_id}/members",
        json={"user_id": fake_user_id},
    )
    assert add_response.status_code == 404
    assert "was not found" in add_response.json()["detail"]
