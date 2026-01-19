from utils import STRONG_PASSWORD


def test_list_password_access_workflow(client_factory, oidc_server, sso_user_token):
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

    # Setup vault
    response = admin_client.post(
        "/api/vault/setup",
        json={"nb_shares": 5, "threshold": 3},
    )
    setup_id = response.json()["setup_id"]
    admin_client.post("/api/vault/validate-setup", json={"setup_id": setup_id})

    # Login SSO user
    sso_client.cookies.set("access_token", sso_user_token["token"])

    # Get admin's personal group ID
    admin_response = admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]

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

    # Step 2: List access - should show only the owner group (pure group model)
    list_access_response = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_response.status_code == 200
    access_data = list_access_response.json()

    assert access_data["resource_id"] == password_id
    # In pure group model, there's only 1 owner: the personal group
    assert len(access_data["access_list"]) == 1

    # The owner should be a group (not the user directly)
    group_access = access_data["access_list"][0]
    assert group_access["is_owner"] is True
    # Owner group has no explicit permissions (ownership is enough)
    assert len(group_access["permissions"]) == 0

    # Step 3: Non-owner should not be able to list access
    list_access_non_owner = sso_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_non_owner.status_code == 403

    # Step 4: Get SSO user's personal group ID
    sso_user_response = sso_client.get("/api/users/me")
    assert sso_user_response.status_code == 200
    sso_user_group_id = sso_user_response.json()["personal_group_id"]

    # Share password with SSO user's personal group
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_user_group_id},
    )
    assert share_response.status_code == 201

    # Step 5: List access - should show owner group + shared group
    list_access_after_share = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_after_share.status_code == 200
    access_data_shared = list_access_after_share.json()

    assert access_data_shared["resource_id"] == password_id
    # Now we have 2: owner group and shared group
    assert len(access_data_shared["access_list"]) == 2

    # Verify owner group is in the list
    owner_group_in_list = next(
        (u for u in access_data_shared["access_list"] if u["is_owner"] is True),
        None,
    )
    assert owner_group_in_list is not None

    # Verify shared group is in the list
    shared_group_in_list = next(
        (
            u
            for u in access_data_shared["access_list"]
            if u["user_id"] == sso_user_group_id
        ),
        None,
    )
    assert shared_group_in_list is not None
    assert shared_group_in_list["is_owner"] is False
    assert "read" in shared_group_in_list["permissions"]
    assert len(shared_group_in_list["permissions"]) == 1

    # Step 6: Unshare password from SSO user's group
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{sso_user_group_id}",
    )
    assert unshare_response.status_code == 204

    # Step 7: List access - should show only owner group again (shared group removed)
    list_access_after_unshare = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_after_unshare.status_code == 200
    access_data_final = list_access_after_unshare.json()

    assert access_data_final["resource_id"] == password_id
    # Back to 1: only owner group
    assert len(access_data_final["access_list"]) == 1

    # Verify the owner group is still there
    owner_group = access_data_final["access_list"][0]
    assert owner_group["is_owner"] is True
