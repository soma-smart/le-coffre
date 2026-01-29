def test_delete_group_workflow(e2e_client, setup):
    """
    Complete workflow: Create group → Delete group → Verify deleted

    This tests the entire group deletion lifecycle:
    1. Admin creates a new group
    2. Verify group exists
    3. Delete the group
    4. Verify group no longer exists
    5. Test edge cases: cannot delete personal group, cannot delete group with passwords
    """
    # Step 1: Setup - Register and login admin (done by setup fixture)
    # Get admin's personal group ID for later tests
    me_response = e2e_client.get("/api/users/me")
    assert me_response.status_code == 200
    personal_group_id = me_response.json()["personal_group_id"]

    # Step 2: CREATE - Create a new group
    create_group_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Test Group to Delete"},
    )
    assert create_group_response.status_code == 201
    group_id = create_group_response.json()["id"]
    assert create_group_response.json()["name"] == "Test Group to Delete"

    # Step 3: READ - Verify group was created
    get_group_response = e2e_client.get(f"/api/groups/{group_id}")
    assert get_group_response.status_code == 200
    assert get_group_response.json()["name"] == "Test Group to Delete"

    # Step 4: DELETE - Delete the group
    delete_response = e2e_client.delete(f"/api/groups/{group_id}")
    assert delete_response.status_code == 204

    # Step 5: VERIFY DELETED - Confirm group no longer exists
    get_deleted_response = e2e_client.get(f"/api/groups/{group_id}")
    assert get_deleted_response.status_code == 404

    # Step 6: Edge case - Cannot delete personal group
    delete_personal_response = e2e_client.delete(f"/api/groups/{personal_group_id}")
    assert delete_personal_response.status_code == 400
    assert "personal group" in delete_personal_response.json()["detail"].lower()

    # Step 7: Edge case - Cannot delete group with passwords
    # Create another group
    create_group2_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Group with Passwords"},
    )
    assert create_group2_response.status_code == 201
    group_with_passwords_id = create_group2_response.json()["id"]

    # Create a password in this group
    create_password_response = e2e_client.post(
        "/api/passwords/",
        json={
            "name": "Test Password",
            "password": "SecureP@ss123",
            "folder": "default",
            "group_id": group_with_passwords_id,
        },
    )
    assert create_password_response.status_code == 201

    # Try to delete group with passwords
    delete_group_with_passwords_response = e2e_client.delete(
        f"/api/groups/{group_with_passwords_id}"
    )
    assert delete_group_with_passwords_response.status_code == 400
    assert (
        "still in use" in delete_group_with_passwords_response.json()["detail"].lower()
        or "still used" in delete_group_with_passwords_response.json()["detail"].lower()
    )

    # Cleanup: Delete the password first, then the group
    password_id = create_password_response.json()["id"]
    delete_password_response = e2e_client.delete(f"/api/passwords/{password_id}")
    assert delete_password_response.status_code == 204

    # Now delete the group (should work)
    delete_group_after_cleanup_response = e2e_client.delete(
        f"/api/groups/{group_with_passwords_id}"
    )
    assert delete_group_after_cleanup_response.status_code == 204
