"""
End-to-end test for complete group update workflow.

This test module covers the entire group update workflow:
1. Create a group
2. Update the group name successfully
3. Verify authorization rules (only owners can update)
4. Attempt to update as non-owner (should fail)
5. Attempt to update personal group (should fail)
6. Attempt to update non-existent group (should fail)
7. Multiple successive updates
8. Verify all updates persist correctly
"""


def test_group_update_complete_workflow(e2e_client, sso_user_factory, client_factory):
    """
    Complete end-to-end workflow testing all group update scenarios:
    1. Create a group and update its name
    2. Verify updates persist
    3. Test multiple successive updates
    4. Verify authorization rules (non-owners cannot update)
    5. Verify cannot update personal groups
    6. Verify cannot update non-existent groups
    """
    # Setup: Register admin (group owner)
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

    # Get admin's personal group for later test
    me_response = e2e_client.get("/api/users/me")
    assert me_response.status_code == 200
    personal_group_id = me_response.json()["personal_group_id"]

    # Step 1: Create a regular group
    create_response = e2e_client.post("/api/groups/", json={"name": "Original Name"})
    assert create_response.status_code == 201

    group = create_response.json()
    assert group["name"] == "Original Name"
    assert "id" in group
    assert group["message"] == "Group created successfully"
    group_id = group["id"]

    # Step 2: Update the group name
    update_response = e2e_client.put(
        f"/api/groups/{group_id}",
        json={"name": "Updated Name"},
    )
    assert update_response.status_code == 200

    updated_group = update_response.json()
    assert updated_group["id"] == group_id
    assert updated_group["name"] == "Updated Name"
    assert updated_group["message"] == "Group updated successfully"

    # Step 3: Verify the update persisted by getting the group
    get_response = e2e_client.get(f"/api/groups/{group_id}")
    assert get_response.status_code == 200

    retrieved_group = get_response.json()
    assert retrieved_group["name"] == "Updated Name"

    # Step 4: Test multiple successive updates
    update2_response = e2e_client.put(
        f"/api/groups/{group_id}",
        json={"name": "Second Update"},
    )
    assert update2_response.status_code == 200
    assert update2_response.json()["name"] == "Second Update"

    update3_response = e2e_client.put(
        f"/api/groups/{group_id}",
        json={"name": "Third Update"},
    )
    assert update3_response.status_code == 200
    assert update3_response.json()["name"] == "Third Update"

    # Verify final state
    final_get_response = e2e_client.get(f"/api/groups/{group_id}")
    assert final_get_response.status_code == 200
    assert final_get_response.json()["name"] == "Third Update"

    # Step 5: Test authorization - create SSO user (non-owner)
    non_owner_user = sso_user_factory("nonowner@example.com", "Non-Owner User")
    non_owner_user_id = non_owner_user["user_id"]

    # Add non-owner as member (not owner) to the group
    add_response = e2e_client.post(
        f"/api/groups/{group_id}/members",
        json={"user_id": non_owner_user_id},
    )
    assert add_response.status_code == 201

    # Create a new client for the non-owner user to avoid cookie conflicts
    non_owner_client = client_factory()
    non_owner_client.cookies.set("access_token", non_owner_user["token"])

    # Step 6: Try to update as non-owner - should fail with 403
    unauthorized_update_response = non_owner_client.put(
        f"/api/groups/{group_id}",
        json={"name": "Unauthorized Update"},
    )
    assert unauthorized_update_response.status_code == 403
    assert "is not an owner of group" in unauthorized_update_response.json()["detail"]

    # Step 7: Verify owner can still update after failed non-owner attempt
    owner_update_response = e2e_client.put(
        f"/api/groups/{group_id}",
        json={"name": "Owner Can Still Update"},
    )
    assert owner_update_response.status_code == 200
    assert owner_update_response.json()["name"] == "Owner Can Still Update"

    # Step 8: Try to update personal group - should fail with 403
    personal_update_response = e2e_client.put(
        f"/api/groups/{personal_group_id}",
        json={"name": "Attempted Personal Group Update"},
    )
    assert personal_update_response.status_code == 403
    assert (
        "Cannot modify members of personal group"
        in personal_update_response.json()["detail"]
    )

    # Step 9: Try to update non-existent group - should fail with 404
    from uuid import uuid4

    non_existent_group_id = uuid4()
    nonexistent_update_response = e2e_client.put(
        f"/api/groups/{non_existent_group_id}",
        json={"name": "This Should Fail"},
    )
    assert nonexistent_update_response.status_code == 404
    assert "was not found" in nonexistent_update_response.json()["detail"]

    # Step 10: Final verification - ensure the group still has the correct name
    final_verification = e2e_client.get(f"/api/groups/{group_id}")
    assert final_verification.status_code == 200
    assert final_verification.json()["name"] == "Owner Can Still Update"
