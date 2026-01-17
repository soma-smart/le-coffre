from utils import STRONG_PASSWORD


def test_share_password_workflow(client_factory, oidc_server, sso_user_token):
    """
    Complete workflow: Create password → Share → Verify access → Unshare → Verify no access
    Uses a second user from SSO to test sharing functionality.

    NOTE: We use separate clients for admin and SSO user to avoid cookie interference.
    """
    # Create separate clients for admin and SSO user to avoid cookie interference
    admin_client = client_factory()
    sso_client = client_factory()

    # Register and login admin to set cookies
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

    # Login SSO user to set cookies on sso_client
    sso_client.cookies.set("access_token", sso_user_token["token"])

    # Get SSO user's personal group ID
    sso_user_response = sso_client.get("/api/users/me")
    assert sso_user_response.status_code == 200
    sso_user_group_id = sso_user_response.json()["personal_group_id"]

    # Step 1: Create a password as owner (admin)
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Shared Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Shared",
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Step 2: Verify owner can read the password
    get_response = admin_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_response.status_code == 200
    assert get_response.json()["password"] == STRONG_PASSWORD

    # Step 3: Verify SSO user cannot access password before sharing
    get_before_share = sso_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_before_share.status_code == 404

    # Step 4: Share password with SSO user's personal group
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_user_group_id},
    )
    assert share_response.status_code == 201
    assert "successfully shared" in share_response.json()["message"]
    assert str(password_id) in share_response.json()["message"]
    assert str(sso_user_group_id) in share_response.json()["message"]

    # Step 5: Verify SSO user can now access the password
    get_after_share = sso_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_after_share.status_code == 200
    assert get_after_share.json()["name"] == "Shared Test Password"
    assert get_after_share.json()["password"] == STRONG_PASSWORD

    # Step 6: Unshare password from the SSO user's group
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{sso_user_group_id}",
    )
    assert unshare_response.status_code == 204

    # Step 7: Verify SSO user can no longer access the password
    get_after_unshare = sso_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_after_unshare.status_code == 404

    # Step 8: Verify owner still has access
    get_owner_final = admin_client.get(
        f"/api/passwords/{password_id}",
    )
    assert get_owner_final.status_code == 200
    assert get_owner_final.json()["password"] == STRONG_PASSWORD


def test_share_password_with_multiple_users(
    client_factory, setup, sso_user_token, second_sso_user_token
):
    """
    Test sharing a password with multiple SSO users (via their personal groups)
    """
    user1_token = sso_user_token["token"]
    user2_token = second_sso_user_token["token"]

    # Create separate clients for admin and each user to avoid cookie interference
    admin_client = client_factory()
    user1_client = client_factory()
    user2_client = client_factory()

    # Setup admin client with cookies
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

    # Setup user clients with cookies
    user1_client.cookies.set("access_token", user1_token)
    user2_client.cookies.set("access_token", user2_token)

    # Get personal group IDs for both users
    user1_response = user1_client.get("/api/users/me")
    assert user1_response.status_code == 200
    user1_group_id = user1_response.json()["personal_group_id"]

    user2_response = user2_client.get("/api/users/me")
    assert user2_response.status_code == 200
    user2_group_id = user2_response.json()["personal_group_id"]

    # Create password
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Multi-Share Password",
            "password": STRONG_PASSWORD,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Share with user 1's personal group
    share1_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": user1_group_id},
    )
    assert share1_response.status_code == 201

    # Share with user 2's personal group
    share2_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": user2_group_id},
    )
    assert share2_response.status_code == 201

    # Verify both users have access
    user1_access = user1_client.get(
        f"/api/passwords/{password_id}",
    )
    assert user1_access.status_code == 200
    assert user1_access.json()["password"] == STRONG_PASSWORD

    user2_access = user2_client.get(
        f"/api/passwords/{password_id}",
    )
    assert user2_access.status_code == 200
    assert user2_access.json()["password"] == STRONG_PASSWORD

    # Unshare with user 1's personal group only
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{user1_group_id}",
    )
    assert unshare_response.status_code == 204

    # Verify user 1 no longer has access
    user1_no_access = user1_client.get(
        f"/api/passwords/{password_id}",
    )
    assert user1_no_access.status_code == 404

    # Verify user 2 still has access
    user2_still_access = user2_client.get(
        f"/api/passwords/{password_id}",
    )
    assert user2_still_access.status_code == 200
    assert user2_still_access.json()["password"] == STRONG_PASSWORD

    # Verify owner still has access
    owner_access = admin_client.get(
        f"/api/passwords/{password_id}",
    )
    assert owner_access.status_code == 200


def test_cannot_unshare_with_owner(authenticated_admin_client, setup):
    """
    Test that owner group cannot be unshared from password
    """
    # Get current user's personal group ID
    me_response = authenticated_admin_client.get("/api/users/me")
    owner_group_id = me_response.json()["personal_group_id"]

    # Create password
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Owner Password",
            "password": STRONG_PASSWORD,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Try to unshare owner group from their own password
    unshare_response = authenticated_admin_client.delete(
        f"/api/passwords/{password_id}/share/{owner_group_id}",
    )
    assert unshare_response.status_code == 400
    assert "owner" in unshare_response.json()["detail"].lower()
