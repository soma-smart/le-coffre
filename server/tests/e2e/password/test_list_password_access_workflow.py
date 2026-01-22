from utils import STRONG_PASSWORD


def test_list_password_access_workflow(
    client_factory, setup, configured_sso, sso_user_token
):
    """
    Complete workflow: Create password → List access (owner only) → Share → List access (owner + shared) → Unshare → List access (owner only)
    """
    # Create separate clients for admin and SSO user
    admin_client = client_factory()
    sso_client = client_factory()

    # Register and login admin
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }
    admin_client.post("/api/auth/register-admin", json=admin_data)
    admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin"},
    )

    # Login SSO user
    sso_client.cookies.set("access_token", sso_user_token["token"])

    # Get admin's personal group ID and user ID
    admin_response = admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]
    admin_user_id = admin_response.json()["id"]

    # Step 1: Create a password as owner
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Access List Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Test",
            "group_id": admin_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Step 2: List access - should show only the owner user (expanded from personal group)
    list_access_response = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_response.status_code == 200
    access_data = list_access_response.json()

    assert access_data["resource_id"] == password_id
    # After expansion, we see the admin user
    assert len(access_data["user_access_list"]) == 1
    assert len(access_data["group_access_list"]) == 1

    # The owner should be the admin user
    user_access = access_data["user_access_list"][0]
    assert user_access["user_id"] == admin_user_id
    assert user_access["is_owner"] is True
    # Owner has no explicit permissions (ownership is enough)
    assert len(user_access["permissions"]) == 0

    # Step 3: Non-owner should not be able to list access
    list_access_non_owner = sso_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_non_owner.status_code == 403

    # Step 4: Get SSO user's personal group ID and user ID
    sso_user_response = sso_client.get("/api/users/me")
    assert sso_user_response.status_code == 200
    sso_user_group_id = sso_user_response.json()["personal_group_id"]
    sso_user_id = sso_user_response.json()["id"]

    # Share password with SSO user's personal group
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_user_group_id},
    )
    assert share_response.status_code == 201

    # Step 5: List access - should show owner user + shared user (both expanded from groups)
    list_access_after_share = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_after_share.status_code == 200
    access_data_shared = list_access_after_share.json()

    assert access_data_shared["resource_id"] == password_id
    # Now we have 2: owner user and shared user
    assert len(access_data_shared["user_access_list"]) == 2
    assert len(access_data_shared["group_access_list"]) == 2

    # Verify owner user is in the list
    owner_user_in_list = next(
        (u for u in access_data_shared["user_access_list"] if u["is_owner"] is True),
        None,
    )
    assert owner_user_in_list is not None
    assert owner_user_in_list["user_id"] == admin_user_id

    # Verify shared user is in the list
    shared_user_in_list = next(
        (
            u
            for u in access_data_shared["user_access_list"]
            if u["user_id"] == sso_user_id
        ),
        None,
    )
    assert shared_user_in_list is not None
    assert shared_user_in_list["is_owner"] is False
    assert "read" in shared_user_in_list["permissions"]
    assert len(shared_user_in_list["permissions"]) == 1

    # Step 6: Unshare password from SSO user's group
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{sso_user_group_id}",
    )
    assert unshare_response.status_code == 204

    # Step 7: List access - should show only owner user again (shared user removed)
    list_access_after_unshare = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_after_unshare.status_code == 200
    access_data_final = list_access_after_unshare.json()

    assert access_data_final["resource_id"] == password_id
    # Back to 1: only owner user
    assert len(access_data_final["user_access_list"]) == 1
    assert len(access_data_final["group_access_list"]) == 1

    # Verify the owner user is still there
    owner_user = access_data_final["user_access_list"][0]
    assert owner_user["user_id"] == admin_user_id
    assert owner_user["is_owner"] is True
