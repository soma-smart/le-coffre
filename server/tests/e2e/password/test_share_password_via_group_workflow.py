"""
End-to-end test for password sharing workflow via groups.

This test module covers password sharing workflows including:
1. Sharing passwords with personal groups
2. Sharing passwords with regular groups where users are members
"""

from utils import STRONG_PASSWORD


def test_share_password_via_group_to_members(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    Complete workflow demonstrating group-based password sharing:
    1. Admin creates a group
    2. Admin adds second user to the group as member
    3. Admin creates a password for their personal group
    4. Admin shares this password to the created group
    5. Check that second user (as group member) has read access to the password

    This test demonstrates that group members (not just owners) can access
    passwords shared with their group.
    """
    # Step 1: Create a second SSO user
    second_user = sso_user_factory("seconduser@example.com", "Second User")
    second_user_id = second_user["user_id"]
    second_user_client = second_user["client"]

    # Get admin's personal group ID
    admin_response = authenticated_admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]

    # Step 2: Admin creates a group
    group_data = {"name": "Engineering Team"}
    create_group_response = authenticated_admin_client.post(
        "/api/groups/", json=group_data
    )
    assert create_group_response.status_code == 201

    group = create_group_response.json()
    assert group["name"] == "Engineering Team"
    assert "id" in group
    group_id = group["id"]

    # Step 3: Admin adds second user to the group as member
    add_member_data = {"user_id": second_user_id}
    add_member_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_member_data
    )
    assert add_member_response.status_code == 201

    add_member_result = add_member_response.json()
    assert add_member_result["group_id"] == group_id
    assert add_member_result["user_id"] == second_user_id
    assert add_member_result["message"] == "Member added successfully"

    # Step 4: Admin creates a password for their personal group
    create_password_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Shared Team Password",
            "password": STRONG_PASSWORD,
            "folder": "Team Credentials",
            "group_id": admin_group_id,
        },
    )
    assert create_password_response.status_code == 201
    password_id = create_password_response.json()["id"]

    # Step 5: Verify admin can read the password
    get_admin_response = authenticated_admin_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_admin_response.status_code == 200
    assert get_admin_response.json()["password"] == STRONG_PASSWORD

    # Step 6: Verify second user cannot access password before sharing
    get_before_share = second_user_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_before_share.status_code == 404

    # Step 7: Admin shares the password to the created group
    share_response = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": group_id},
    )
    assert share_response.status_code == 201
    assert "successfully shared" in share_response.json()["message"]

    # Step 8: Verify second user now has read access to the password (as group member)
    get_after_share = second_user_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_after_share.status_code == 200
    shared_password_data = get_after_share.json()
    assert shared_password_data["name"] == "Shared Team Password"
    assert shared_password_data["password"] == STRONG_PASSWORD
    assert shared_password_data["folder"] == "Team Credentials"

    # Step 9: Verify the password appears in second user's password list
    list_response = second_user_client.get("/api/passwords/list")
    assert list_response.status_code == 200
    passwords_list = list_response.json()
    assert any(pwd["id"] == password_id for pwd in passwords_list)


def test_share_password_via_personal_group_workflow(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    Complete workflow for sharing via personal groups:
    1. Admin creates a group
    2. Admin adds second user to the group as member
    3. Admin creates a password for their personal group
    4. Admin shares this password to the second user's PERSONAL group
    5. Check that second user has read access to the password

    This test demonstrates the current working implementation where passwords
    are shared with a user's personal group (where they are the owner).
    """
    # Step 1: Create a second SSO user
    second_user = sso_user_factory("seconduser@example.com", "Second User")
    second_user_id = second_user["user_id"]
    second_user_client = second_user["client"]

    # Get second user's personal group ID
    second_user_response = second_user_client.get("/api/users/me")
    assert second_user_response.status_code == 200
    second_user_personal_group_id = second_user_response.json()["personal_group_id"]

    # Get admin's personal group ID
    admin_response = authenticated_admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]

    # Step 2: Admin creates a group (for context, but not used for sharing in this test)
    group_data = {"name": "Engineering Team"}
    create_group_response = authenticated_admin_client.post(
        "/api/groups/", json=group_data
    )
    assert create_group_response.status_code == 201

    group = create_group_response.json()
    assert group["name"] == "Engineering Team"
    assert "id" in group
    group_id = group["id"]

    # Step 3: Admin adds second user to the group as member
    add_member_data = {"user_id": second_user_id}
    add_member_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json=add_member_data
    )
    assert add_member_response.status_code == 201

    add_member_result = add_member_response.json()
    assert add_member_result["group_id"] == group_id
    assert add_member_result["user_id"] == second_user_id
    assert add_member_result["message"] == "Member added successfully"

    # Step 4: Admin creates a password for their personal group
    create_password_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Shared Team Password",
            "password": STRONG_PASSWORD,
            "folder": "Team Credentials",
            "group_id": admin_group_id,
        },
    )
    assert create_password_response.status_code == 201
    password_id = create_password_response.json()["id"]

    # Step 5: Verify admin can read the password
    get_admin_response = authenticated_admin_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_admin_response.status_code == 200
    assert get_admin_response.json()["password"] == STRONG_PASSWORD

    # Step 6: Verify second user cannot access password before sharing
    get_before_share = second_user_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_before_share.status_code == 404

    # Step 7: Admin shares the password to the ENGINEERING TEAM group
    share_response = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": group_id},
    )
    assert share_response.status_code == 201
    assert "successfully shared" in share_response.json()["message"]

    # Step 8: Verify second user now has read access to the password
    get_after_share = second_user_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_after_share.status_code == 200
    shared_password_data = get_after_share.json()
    assert shared_password_data["name"] == "Shared Team Password"
    assert shared_password_data["password"] == STRONG_PASSWORD
    assert shared_password_data["folder"] == "Team Credentials"

    # Step 9: Verify the password appears in second user's password list
    list_response = second_user_client.get("/api/passwords/list")
    assert list_response.status_code == 200
    passwords_list = list_response.json()
    assert any(pwd["id"] == password_id for pwd in passwords_list)

    # Step 10: Delete shared link to ENGINEERING TEAM
    unshare_response = authenticated_admin_client.delete(
        f"/api/passwords/{password_id}/share/{group_id}",
    )

    assert unshare_response.status_code == 204

    # Step 11: Check that second user cannot read the password anymore
    get_after_share = second_user_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_after_share.status_code == 404


def test_share_password_via_group_with_multiple_members(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    Test sharing a password to a group with multiple members.
    All members should have read access to the shared password.
    """
    # Create multiple SSO users
    user1 = sso_user_factory("user1@example.com", "User One")
    user1_id = user1["user_id"]
    user1_client = user1["client"]

    user2 = sso_user_factory("user2@example.com", "User Two")
    user2_id = user2["user_id"]
    user2_client = user2["client"]

    user3 = sso_user_factory("user3@example.com", "User Three")
    user3_id = user3["user_id"]
    user3_client = user3["client"]

    # Get admin's personal group ID
    admin_response = authenticated_admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]

    # Admin creates a group
    group_response = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Development Team"}
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Admin adds all users to the group
    for user_id in [user1_id, user2_id, user3_id]:
        add_response = authenticated_admin_client.post(
            f"/api/groups/{group_id}/members", json={"user_id": user_id}
        )
        assert add_response.status_code == 201

    # Admin creates a password
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Team Database Password",
            "password": STRONG_PASSWORD,
            "group_id": admin_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Admin shares password to the group
    share_response = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": group_id},
    )
    assert share_response.status_code == 201

    # Verify all users have read access
    for user_client, user_name in [
        (user1_client, "User One"),
        (user2_client, "User Two"),
        (user3_client, "User Three"),
    ]:
        get_response = user_client.get(f"/api/passwords/{password_id}")
        assert get_response.status_code == 200
        assert get_response.json()["password"] == STRONG_PASSWORD
        assert get_response.json()["name"] == "Team Database Password"


def test_removed_group_member_loses_access(
    authenticated_admin_client, sso_user_factory, setup
):
    """
    Test that when a user is removed from a group, they lose access
    to passwords shared with that group.
    """
    # Create a SSO user
    user = sso_user_factory("user@example.com", "Test User")
    user_id = user["user_id"]
    user_client = user["client"]

    # Get admin's personal group ID
    admin_response = authenticated_admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]

    # Admin creates a group and adds the user
    group_response = authenticated_admin_client.post(
        "/api/groups/", json={"name": "Project Team"}
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    add_response = authenticated_admin_client.post(
        f"/api/groups/{group_id}/members", json={"user_id": user_id}
    )
    assert add_response.status_code == 201

    # Admin creates and shares a password to the group
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Project Secret",
            "password": STRONG_PASSWORD,
            "group_id": admin_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    share_response = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": group_id},
    )
    assert share_response.status_code == 201

    # Verify user has access
    get_response = user_client.get(f"/api/passwords/{password_id}")
    assert get_response.status_code == 200
    assert get_response.json()["password"] == STRONG_PASSWORD

    # Admin removes user from the group
    remove_response = authenticated_admin_client.delete(
        f"/api/groups/{group_id}/members/{user_id}"
    )
    assert remove_response.status_code == 200

    # Verify user no longer has access to the password
    get_after_removal = user_client.get(f"/api/passwords/{password_id}")
    assert get_after_removal.status_code == 404

    # Verify the password doesn't appear in user's password list
    list_response = user_client.get("/api/passwords/list")
    assert list_response.status_code == 200
    passwords_list = list_response.json()
    assert not any(pwd["id"] == password_id for pwd in passwords_list)
