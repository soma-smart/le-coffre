"""
Complete End-to-End Groups Workflow.

This test covers the entire group management system in one comprehensive workflow:
1. List/get groups (structure, personal flag, owners/members fields)
2. Authentication requirements
3. Group CRUD (create, read, update)
4. Member management (add, remove, idempotency, authorization)
5. Owner promotion (promote, idempotency, authorization)
6. Edge cases (non-existent user/group, personal group restrictions)
"""

from uuid import uuid4


def test_complete_groups_workflow(
    authenticated_admin_client, sso_user_factory, client_factory
):
    """
    Complete groups workflow covering all group management features step by step.
    """

    # =========================================================================
    # SETUP: Create SSO users used throughout the test
    # =========================================================================
    user1 = sso_user_factory("user1@example.com", "User One")
    user1_id = user1["user_id"]
    user1_client = user1["client"]

    user2 = sso_user_factory("user2@example.com", "User Two")
    user2_id = user2["user_id"]

    owner_user = sso_user_factory("owner@example.com", "Future Owner")
    owner_user_id = owner_user["user_id"]
    owner_user_client = owner_user["client"]

    non_owner_user = sso_user_factory("nonowner@example.com", "Non-Owner User")
    non_owner_user_id = non_owner_user["user_id"]
    non_owner_client = client_factory()
    non_owner_client.cookies.set("access_token", non_owner_user["token"])

    # =========================================================================
    # PHASE 1: GET AND LIST GROUPS
    # =========================================================================

    # Step 1.1: Get SSO user's own ID
    user_response = user1_client.get("/api/users/me")
    assert user_response.status_code == 200
    sso_user_id = user_response.json()["id"]

    # Step 1.2: Create a shared group as SSO user
    create_group_response = user1_client.post(
        "/api/groups/",
        json={"name": "Engineering Team"},
    )
    assert create_group_response.status_code == 201
    sso_group_id = create_group_response.json()["id"]

    # Step 1.3: List all groups (include_personal=true)
    list_all_response = user1_client.get("/api/groups?include_personal=true")
    assert list_all_response.status_code == 200
    all_groups = list_all_response.json()
    assert all_groups["total"] >= 2  # At least personal + shared
    assert len(all_groups["groups"]) >= 2
    assert any(g["is_personal"] for g in all_groups["groups"]), "Should have personal group"
    assert any(not g["is_personal"] for g in all_groups["groups"]), "Should have shared group"

    # Step 1.4: List only shared groups (include_personal=false)
    list_shared_response = user1_client.get("/api/groups?include_personal=false")
    assert list_shared_response.status_code == 200
    shared_groups = list_shared_response.json()
    assert shared_groups["total"] >= 1
    for group in shared_groups["groups"]:
        assert not group["is_personal"], "Should only return shared groups"
    assert any(g["id"] == sso_group_id for g in shared_groups["groups"])

    # Step 1.5: Default list (no include_personal flag) should match include_personal=true
    default_response = user1_client.get("/api/groups")
    assert default_response.status_code == 200
    default = default_response.json()
    assert default["total"] == all_groups["total"]

    # Step 1.6: include_personal=true should have >= groups than include_personal=false
    assert all_groups["total"] >= shared_groups["total"]

    # Step 1.7: Get a specific shared group by ID
    get_group_response = user1_client.get(f"/api/groups/{sso_group_id}")
    assert get_group_response.status_code == 200
    retrieved_group = get_group_response.json()
    assert retrieved_group["id"] == sso_group_id
    assert retrieved_group["name"] == "Engineering Team"
    assert retrieved_group["is_personal"] is False
    assert retrieved_group["user_id"] is None
    assert "owners" in retrieved_group
    assert "members" in retrieved_group
    assert isinstance(retrieved_group["owners"], list)
    assert isinstance(retrieved_group["members"], list)
    assert sso_user_id in retrieved_group["owners"]  # Creator is an owner

    # Step 1.8: Get and verify personal group
    all_with_personal = user1_client.get("/api/groups?include_personal=true").json()
    personal_groups = [g for g in all_with_personal["groups"] if g["is_personal"]]
    assert len(personal_groups) > 0, "Should have at least one personal group"
    personal_group = personal_groups[0]

    get_personal_response = user1_client.get(f"/api/groups/{personal_group['id']}")
    assert get_personal_response.status_code == 200
    retrieved_personal = get_personal_response.json()
    assert retrieved_personal["id"] == personal_group["id"]
    assert retrieved_personal["is_personal"] is True
    assert retrieved_personal["user_id"] is not None

    # Step 1.9: Verify owners/members structure on a fresh group
    fresh_group_response = user1_client.post("/api/groups/", json={"name": "Test Team"})
    assert fresh_group_response.status_code == 201
    fresh_group_id = fresh_group_response.json()["id"]
    get_fresh_response = user1_client.get(f"/api/groups/{fresh_group_id}")
    assert get_fresh_response.status_code == 200
    fresh_group = get_fresh_response.json()
    assert "owners" in fresh_group
    assert "members" in fresh_group
    assert isinstance(fresh_group["owners"], list)
    assert isinstance(fresh_group["members"], list)
    assert sso_user_id in fresh_group["owners"]
    assert fresh_group["is_personal"] is False

    # =========================================================================
    # PHASE 2: AUTHENTICATION REQUIREMENTS
    # =========================================================================

    unauthenticated_client = client_factory()

    # Step 2.1: Getting a group requires authentication
    unauth_get_response = unauthenticated_client.get(f"/api/groups/{sso_group_id}")
    assert unauth_get_response.status_code == 401

    # Step 2.2: Listing groups requires authentication
    unauth_list_response = unauthenticated_client.get("/api/groups")
    assert unauth_list_response.status_code == 401

    # Step 2.3: Creating a group requires authentication
    unauth_create_response = unauthenticated_client.post(
        "/api/groups/", json={"name": "Unauthorized Group"}
    )
    assert unauth_create_response.status_code == 401

    # Step 2.4: Get non-existent group returns 404
    non_existent_id = uuid4()
    not_found_response = user1_client.get(f"/api/groups/{non_existent_id}")
    assert not_found_response.status_code == 404
    assert "not found" in not_found_response.json()["detail"].lower()

    # =========================================================================
    # PHASE 3: GROUP UPDATE
    # =========================================================================

    # Step 3.1: Create a group as admin
    admin_me_response = authenticated_admin_client.get("/api/users/me")
    assert admin_me_response.status_code == 200
    admin_personal_group_id = admin_me_response.json()["personal_group_id"]

    create_response = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Original Name"}
    )
    assert create_response.status_code == 201
    group_for_update = create_response.json()
    assert group_for_update["name"] == "Original Name"
    assert "id" in group_for_update
    assert group_for_update["message"] == "Group created successfully"
    updatable_group_id = group_for_update["id"]

    # Step 3.2: Update the group name
    update_response = authenticated_admin_client.put(
        f"/api/groups/{updatable_group_id}",
        json={"name": "Updated Name"},
    )
    assert update_response.status_code == 200
    updated_group = update_response.json()
    assert updated_group["id"] == updatable_group_id
    assert updated_group["name"] == "Updated Name"
    assert updated_group["message"] == "Group updated successfully"

    # Step 3.3: Verify update persisted
    get_updated_response = authenticated_admin_client.get(f"/api/groups/{updatable_group_id}")
    assert get_updated_response.status_code == 200
    assert get_updated_response.json()["name"] == "Updated Name"

    # Step 3.4: Multiple successive updates
    update2_response = authenticated_admin_client.put(
        f"/api/groups/{updatable_group_id}", json={"name": "Second Update"}
    )
    assert update2_response.status_code == 200
    assert update2_response.json()["name"] == "Second Update"

    update3_response = authenticated_admin_client.put(
        f"/api/groups/{updatable_group_id}", json={"name": "Third Update"}
    )
    assert update3_response.status_code == 200
    assert update3_response.json()["name"] == "Third Update"

    final_state_response = authenticated_admin_client.get(f"/api/groups/{updatable_group_id}")
    assert final_state_response.status_code == 200
    assert final_state_response.json()["name"] == "Third Update"

    # Step 3.5: Add non-owner as member so we can test update authorization
    authenticated_admin_client.post(
        f"/api/groups/{updatable_group_id}/members",
        json={"user_id": non_owner_user_id},
    )

    # Step 3.6: Non-owner cannot update the group
    unauthorized_update_response = non_owner_client.put(
        f"/api/groups/{updatable_group_id}",
        json={"name": "Unauthorized Update"},
    )
    assert unauthorized_update_response.status_code == 403
    assert "is not an owner of group" in unauthorized_update_response.json()["detail"]

    # Step 3.7: Owner can still update after failed non-owner attempt
    owner_update_response = authenticated_admin_client.put(
        f"/api/groups/{updatable_group_id}",
        json={"name": "Owner Can Still Update"},
    )
    assert owner_update_response.status_code == 200
    assert owner_update_response.json()["name"] == "Owner Can Still Update"

    # Step 3.8: Cannot update personal group
    personal_update_response = authenticated_admin_client.put(
        f"/api/groups/{admin_personal_group_id}",
        json={"name": "Attempted Personal Group Update"},
    )
    assert personal_update_response.status_code == 403
    assert (
        "Cannot modify members of personal group"
        in personal_update_response.json()["detail"]
    )

    # Step 3.9: Cannot update non-existent group
    nonexistent_update_response = authenticated_admin_client.put(
        f"/api/groups/{uuid4()}",
        json={"name": "This Should Fail"},
    )
    assert nonexistent_update_response.status_code == 404
    assert "was not found" in nonexistent_update_response.json()["detail"]

    # Step 3.10: Final verification - group still has the correct name
    final_verification = authenticated_admin_client.get(f"/api/groups/{updatable_group_id}")
    assert final_verification.status_code == 200
    assert final_verification.json()["name"] == "Owner Can Still Update"

    # =========================================================================
    # PHASE 4: MEMBER MANAGEMENT
    # =========================================================================

    # Step 4.1: Create group for member management tests
    group_for_members = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Engineering Team"}
    )
    assert group_for_members.status_code == 201
    group = group_for_members.json()
    assert group["name"] == "Engineering Team"
    assert "id" in group
    assert group["message"] == "Group created successfully"
    members_group_id = group["id"]

    # Step 4.2: Add user1 to the group
    add_user1_response = authenticated_admin_client.post(
        f"/api/groups/{members_group_id}/members", json={"user_id": user1_id}
    )
    assert add_user1_response.status_code == 201
    add_user1_result = add_user1_response.json()
    assert add_user1_result["group_id"] == members_group_id
    assert add_user1_result["user_id"] == user1_id
    assert add_user1_result["message"] == "Member added successfully"

    # Step 4.3: Add user2 to the group
    add_user2_response = authenticated_admin_client.post(
        f"/api/groups/{members_group_id}/members", json={"user_id": user2_id}
    )
    assert add_user2_response.status_code == 201

    # Step 4.4: Idempotency - adding user1 again should succeed
    add_user1_again_response = authenticated_admin_client.post(
        f"/api/groups/{members_group_id}/members", json={"user_id": user1_id}
    )
    assert add_user1_again_response.status_code == 201

    # Step 4.5: Remove user2 from the group
    remove_user2_response = authenticated_admin_client.delete(
        f"/api/groups/{members_group_id}/members/{user2_id}"
    )
    assert remove_user2_response.status_code == 200, remove_user2_response.text
    assert remove_user2_response.json()["message"] == "Member removed successfully"

    # Step 4.6: Cannot remove user that is no longer a member
    remove_nonmember_response = authenticated_admin_client.delete(
        f"/api/groups/{members_group_id}/members/{user2_id}"
    )
    assert remove_nonmember_response.status_code == 400
    assert "is not a member of group" in remove_nonmember_response.json()["detail"]

    # Step 4.7: Cannot add a non-existent user
    fake_user_id = "00000000-0000-0000-0000-000000000000"
    add_fake_user_response = authenticated_admin_client.post(
        f"/api/groups/{members_group_id}/members",
        json={"user_id": fake_user_id},
    )
    assert add_fake_user_response.status_code == 404
    assert "was not found" in add_fake_user_response.json()["detail"]

    # =========================================================================
    # PHASE 5: MEMBER AUTHORIZATION
    # =========================================================================

    # Step 5.1: Create group for authorization tests
    auth_group_response = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Test Group"}
    )
    assert auth_group_response.status_code == 201
    admin_group_id = auth_group_response.json()["id"]

    # Step 5.2: Add user1 as a member
    authenticated_admin_client.post(
        f"/api/groups/{admin_group_id}/members", json={"user_id": user1_id}
    )

    # Step 5.3: Non-owner (non_owner_user) cannot add members to the group
    add_as_non_owner_response = non_owner_client.post(
        f"/api/groups/{admin_group_id}/members",
        json={"user_id": non_owner_user_id},
    )
    assert add_as_non_owner_response.status_code == 403
    assert "is not an owner of group" in add_as_non_owner_response.json()["detail"]

    # Step 5.4: Non-owner cannot remove members from the group
    remove_as_non_owner_response = non_owner_client.delete(
        f"/api/groups/{admin_group_id}/members/{user1_id}"
    )
    assert remove_as_non_owner_response.status_code == 403
    assert "is not an owner of group" in remove_as_non_owner_response.json()["detail"]

    # Step 5.5: Get admin's own user ID to test owner removal
    admin_id = admin_me_response.json()["id"]

    # Step 5.6: Cannot remove an owner from the group
    remove_owner_response = authenticated_admin_client.delete(
        f"/api/groups/{admin_group_id}/members/{admin_id}"
    )
    assert remove_owner_response.status_code == 400
    assert "Cannot remove owner" in remove_owner_response.json()["detail"]

    # =========================================================================
    # PHASE 6: OWNER PROMOTION
    # =========================================================================

    # Step 6.1: Create a group for ownership tests (admin is owner)
    ownership_group_response = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Leadership Team"}
    )
    assert ownership_group_response.status_code == 201
    ownership_group_data = ownership_group_response.json()
    assert ownership_group_data["name"] == "Leadership Team"
    ownership_group_id = ownership_group_data["id"]

    # Step 6.2: Add owner_user as a member (not an owner yet)
    authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/members", json={"user_id": owner_user_id}
    )

    # Step 6.3: Verify owner_user is a member but not an owner
    get_group_before = authenticated_admin_client.get(f"/api/groups/{ownership_group_id}")
    assert get_group_before.status_code == 200
    group_before = get_group_before.json()
    assert owner_user_id in group_before["members"]
    assert owner_user_id not in group_before["owners"]

    # Step 6.4: Promote owner_user to owner
    add_owner_response = authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/owners", json={"user_id": owner_user_id}
    )
    assert add_owner_response.status_code == 201
    add_owner_result = add_owner_response.json()
    assert add_owner_result["group_id"] == ownership_group_id
    assert add_owner_result["user_id"] == owner_user_id
    assert add_owner_result["message"] == "Owner added successfully"

    # Step 6.5: Verify owner_user is now an owner and no longer in members
    get_group_after = authenticated_admin_client.get(f"/api/groups/{ownership_group_id}")
    assert get_group_after.status_code == 200
    group_after = get_group_after.json()
    assert owner_user_id in group_after["owners"]
    assert owner_user_id not in group_after["members"]

    # Step 6.6: Idempotency - promoting owner_user again should succeed
    add_owner_again_response = authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/owners", json={"user_id": owner_user_id}
    )
    assert add_owner_again_response.status_code == 201

    # Step 6.7: Cannot promote a non-member to owner
    add_nonmember_as_owner_response = authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/owners", json={"user_id": user2_id}
    )
    assert add_nonmember_as_owner_response.status_code == 400
    assert "not a member" in add_nonmember_as_owner_response.json()["detail"].lower()

    # Step 6.8: Add user2 as a member so owner_user can promote them
    authenticated_admin_client.post(
        f"/api/groups/{ownership_group_id}/members", json={"user_id": user2_id}
    )

    # Step 6.9: owner_user (who is now an owner) can promote user2
    promote_user2_response = owner_user_client.post(
        f"/api/groups/{ownership_group_id}/owners", json={"user_id": user2_id}
    )
    assert promote_user2_response.status_code == 201

    # Step 6.10: Verify user2 is now an owner
    final_group_response = authenticated_admin_client.get(f"/api/groups/{ownership_group_id}")
    assert final_group_response.status_code == 200
    final_group = final_group_response.json()
    assert user2_id in final_group["owners"]

    # =========================================================================
    # PHASE 7: OWNER PROMOTION AUTHORIZATION
    # =========================================================================

    # Step 7.1: Create group and add members for authorization test
    restricted_group_response = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Restricted Team"}
    )
    assert restricted_group_response.status_code == 201
    restricted_group_id = restricted_group_response.json()["id"]

    # Add non_owner and owner_user as plain members
    authenticated_admin_client.post(
        f"/api/groups/{restricted_group_id}/members", json={"user_id": non_owner_user_id}
    )
    user3 = sso_user_factory("target@example.com", "Target User")
    user3_id = user3["user_id"]
    authenticated_admin_client.post(
        f"/api/groups/{restricted_group_id}/members", json={"user_id": user3_id}
    )

    # Step 7.2: Non-owner cannot promote members to owner
    non_owner_promote_response = non_owner_client.post(
        f"/api/groups/{restricted_group_id}/owners", json={"user_id": user3_id}
    )
    assert non_owner_promote_response.status_code == 403
    assert "not an owner" in non_owner_promote_response.json()["detail"].lower()

    # Step 7.3: Cannot add owner to a personal group
    personal_groups_response = authenticated_admin_client.get(
        "/api/groups?include_personal=true"
    )
    all_groups_list = personal_groups_response.json()["groups"]
    admin_personal_group = next((g for g in all_groups_list if g["is_personal"]), None)
    assert admin_personal_group is not None

    add_owner_to_personal_response = authenticated_admin_client.post(
        f"/api/groups/{admin_personal_group['id']}/owners",
        json={"user_id": non_owner_user_id},
    )
    assert add_owner_to_personal_response.status_code == 403
    assert (
        "personal group" in add_owner_to_personal_response.json()["detail"].lower()
        or "cannot modify" in add_owner_to_personal_response.json()["detail"].lower()
    )
