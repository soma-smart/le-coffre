from utils import STRONG_PASSWORD


def test_list_password_access_workflow(client_factory, oidc_server, sso_user_token):
    """
    Complete workflow: Create password → List access (owner only) → Share → List access (owner + shared) → Unshare → List access (owner only)
    """
    shared_user_id = sso_user_token["user_id"]

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

    # Get admin user ID
    me_response = admin_client.get("/api/users/me")
    admin_user_id = me_response.json()["id"]

    # Setup vault
    response = admin_client.post(
        "/api/vault/setup",
        json={"nb_shares": 5, "threshold": 3},
    )
    setup_id = response.json()["setup_id"]
    admin_client.post("/api/vault/validate-setup", json={"setup_id": setup_id})

    # Login SSO user
    sso_client.cookies.set("access_token", sso_user_token["token"])

    # Step 1: Create a password as owner
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Access List Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Test",
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Step 2: List access - should show only owner
    list_access_response = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_response.status_code == 200
    access_data = list_access_response.json()

    assert access_data["resource_id"] == password_id
    assert len(access_data["access_list"]) == 1

    owner_access = access_data["access_list"][0]
    assert owner_access["user_id"] == admin_user_id
    assert owner_access["is_owner"] is True
    assert owner_access["permissions"] == []  # Owner has empty permission set

    # Step 3: Non-owner should not be able to list access
    list_access_non_owner = sso_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_non_owner.status_code == 403

    # Step 4: Share password with SSO user
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": shared_user_id},
    )
    assert share_response.status_code == 201

    # Step 5: List access - should show owner + shared user
    list_access_after_share = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_after_share.status_code == 200
    access_data_shared = list_access_after_share.json()

    assert access_data_shared["resource_id"] == password_id
    assert len(access_data_shared["access_list"]) == 2

    # Verify owner is in the list
    owner_in_list = next(
        (u for u in access_data_shared["access_list"] if u["user_id"] == admin_user_id),
        None,
    )
    assert owner_in_list is not None
    assert owner_in_list["is_owner"] is True

    # Verify shared user is in the list
    shared_user_in_list = next(
        (
            u
            for u in access_data_shared["access_list"]
            if u["user_id"] == shared_user_id
        ),
        None,
    )
    assert shared_user_in_list is not None
    assert shared_user_in_list["is_owner"] is False
    assert "read" in shared_user_in_list["permissions"]
    assert len(shared_user_in_list["permissions"]) == 1

    # Step 6: Unshare password from SSO user
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{shared_user_id}",
    )
    assert unshare_response.status_code == 204

    # Step 7: List access - should show only owner again
    list_access_after_unshare = admin_client.get(f"/api/passwords/{password_id}/access")
    assert list_access_after_unshare.status_code == 200
    access_data_final = list_access_after_unshare.json()

    assert access_data_final["resource_id"] == password_id
    assert len(access_data_final["access_list"]) == 1
    assert access_data_final["access_list"][0]["user_id"] == admin_user_id
    assert access_data_final["access_list"][0]["is_owner"] is True
