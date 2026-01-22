def test_add_owner_to_group_workflow(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    End-to-end test that:
    1. Creates a group with admin as owner
    2. Creates two users
    3. Adds user1 as a member
    4. Promotes user1 to owner
    5. Verifies user1 is now an owner
    6. Verifies non-owner (user2) cannot promote members
    7. Verifies cannot promote non-members
    """
    # Step 1: Create two users
    user1 = sso_user_factory("owner@example.com", "Future Owner")
    user1_id = user1["user_id"]

    user2 = sso_user_factory("member@example.com", "Regular Member")
    user2_id = user2["user_id"]

    # Step 2: Create a group (admin is owner)
    group_data = {"name": "Leadership Team"}
    create_group_response = authenticated_admin_client.post(
        "/api/groups/", json=group_data
    )
    assert create_group_response.status_code == 201

    group = create_group_response.json()
    assert group["name"] == "Leadership Team"
    group_id = group["id"]

    # Step 3: Add user1 as a member (not an owner yet)
    add_member_data = {"user_id": user1_id}
    add_member_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_member_data
    )
    assert add_member_response.status_code == 201

    # Step 4: Verify user1 is a member but not an owner
    get_group_response = authenticated_admin_client.get(f"/api/groups/{group_id}")
    assert get_group_response.status_code == 200

    group_details = get_group_response.json()
    assert user1_id in group_details["members"]
    assert user1_id not in group_details["owners"]

    # Step 5: Promote user1 to owner
    add_owner_data = {"user_id": user1_id}
    add_owner_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/owners", json=add_owner_data
    )
    assert add_owner_response.status_code == 201

    add_owner_result = add_owner_response.json()
    assert add_owner_result["group_id"] == group_id
    assert add_owner_result["user_id"] == user1_id
    assert add_owner_result["message"] == "Owner added successfully"

    # Step 6: Verify user1 is now an owner
    get_group_after_response = authenticated_admin_client.get(f"/api/groups/{group_id}")
    assert get_group_after_response.status_code == 200

    group_after = get_group_after_response.json()
    assert user1_id in group_after["owners"]
    assert user1_id not in group_after["members"]  # Owners are not in members list

    # Step 7: Verify idempotency - promoting user1 again should succeed
    add_owner_again_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/owners", json=add_owner_data
    )
    assert add_owner_again_response.status_code == 201

    # Step 8: Verify cannot promote a non-member
    add_nonmember_as_owner_data = {"user_id": user2_id}
    add_nonmember_as_owner_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/owners", json=add_nonmember_as_owner_data
    )
    assert add_nonmember_as_owner_response.status_code == 400
    assert "not a member" in add_nonmember_as_owner_response.json()["detail"].lower()

    # Step 9: Add user2 as a member first
    add_user2_member_data = {"user_id": user2_id}
    authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_user2_member_data
    )

    # Step 10: Now user1 (who is an owner) should be able to promote user2
    # First, authenticate as user1
    user1_client = user1["client"]

    promote_user2_data = {"user_id": user2_id}
    promote_user2_response = user1_client.post(
        f"/api/groups/{group_id}/owners", json=promote_user2_data
    )
    assert promote_user2_response.status_code == 201

    # Step 11: Verify user2 is now an owner
    final_group_response = authenticated_admin_client.get(f"/api/groups/{group_id}")
    assert final_group_response.status_code == 200

    final_group = final_group_response.json()
    assert user2_id in final_group["owners"]


def test_add_owner_authorization_rules(authenticated_admin_client, sso_user_factory):
    """
    Test authorization rules for adding owners:
    1. Non-owners cannot promote members to owners
    2. Cannot promote to personal groups
    """
    # Step 1: Create a user who is not a group owner
    regular_user = sso_user_factory("regular@example.com", "Regular User")
    regular_user_id = regular_user["user_id"]
    regular_user_client = regular_user["client"]

    target_user = sso_user_factory("target@example.com", "Target User")
    target_user_id = target_user["user_id"]

    # Step 2: Create a group (admin is owner)
    group_data = {"name": "Restricted Team"}
    create_group_response = authenticated_admin_client.post(
        "/api/groups/", json=group_data
    )
    assert create_group_response.status_code == 201
    group_id = create_group_response.json()["id"]

    # Step 3: Add both users as regular members
    authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json={"user_id": regular_user_id}
    )
    authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json={"user_id": target_user_id}
    )

    # Step 4: Verify non-owner cannot promote members
    promote_data = {"user_id": target_user_id}
    unauthorized_response = regular_user_client.post(
        f"/api/groups/{group_id}/owners", json=promote_data
    )
    assert unauthorized_response.status_code == 403
    assert "not an owner" in unauthorized_response.json()["detail"].lower()

    # Step 5: Try to add owner to a personal group (should fail)
    list_groups_response = authenticated_admin_client.get(
        "/api/groups?include_personal=true"
    )
    groups = list_groups_response.json()["groups"]

    # Find admin's personal group
    personal_group = next((g for g in groups if g["is_personal"]), None)
    assert personal_group is not None

    # Try to add owner to personal group
    add_owner_to_personal_response = authenticated_admin_client.post(
        f"/api/groups/{personal_group['id']}/owners", json={"user_id": regular_user_id}
    )
    assert add_owner_to_personal_response.status_code == 403
    assert (
        "personal group" in add_owner_to_personal_response.json()["detail"].lower()
        or "cannot modify" in add_owner_to_personal_response.json()["detail"].lower()
    )
