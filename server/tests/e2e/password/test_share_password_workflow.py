from uuid import UUID, uuid4
import jwt

STRONG_PASSWORD = "StrongP@ssw0rd123"


def get_user_id_from_token(token: str) -> str:
    """Extract user_id from JWT token"""
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded["user_id"]


def test_share_password_workflow(e2e_client, setup, admin_token):
    """
    Complete workflow: Create password → Share → Verify access → Unshare → Verify no access
    """
    # Setup users - use admin as owner since they have the auth token
    owner_id = get_user_id_from_token(admin_token)
    
    # Create a user to share with
    shared_user_response = e2e_client.post(
        "/api/users/",
        json={
            "username": "shareduser",
            "email": "shared@example.com",
            "name": "Shared User",
        },
    )
    assert shared_user_response.status_code == 201
    shared_user_id = shared_user_response.json()["id"]

    # Step 1: Create a password as owner
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": owner_id,
            "name": "Shared Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Shared",
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]
    assert create_response.json()["name"] == "Shared Test Password"

    # Step 2: Verify owner can read the password
    get_response = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={owner_id}"
    )
    assert get_response.status_code == 200
    assert get_response.json()["password"] == STRONG_PASSWORD

    # Step 3: Verify shared user cannot access password before sharing
    get_before_share = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={shared_user_id}"
    )
    assert get_before_share.status_code == 404

    # Step 4: Share password with another user
    share_response = e2e_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": shared_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share_response.status_code == 200
    assert "successfully shared" in share_response.json()["message"]
    assert str(password_id) in share_response.json()["message"]
    assert str(shared_user_id) in share_response.json()["message"]

    # Step 5: Verify shared user can now access the password
    get_after_share = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={shared_user_id}"
    )
    assert get_after_share.status_code == 200
    assert get_after_share.json()["name"] == "Shared Test Password"
    assert get_after_share.json()["password"] == STRONG_PASSWORD

    # Step 6: Unshare password from the shared user
    unshare_response = e2e_client.delete(
        f"/api/passwords/{password_id}/share/{shared_user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unshare_response.status_code == 200
    assert "access revoked" in unshare_response.json()["message"]
    assert str(password_id) in unshare_response.json()["message"]
    assert str(shared_user_id) in unshare_response.json()["message"]

    # Step 7: Verify shared user can no longer access the password
    get_after_unshare = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={shared_user_id}"
    )
    assert get_after_unshare.status_code == 404

    # Step 8: Verify owner still has access
    get_owner_final = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={owner_id}"
    )
    assert get_owner_final.status_code == 200
    assert get_owner_final.json()["password"] == STRONG_PASSWORD


def test_share_password_with_multiple_users(e2e_client, setup, admin_token):
    """
    Test sharing a password with multiple users
    """
    owner_id = get_user_id_from_token(admin_token)
    
    # Create users to share with
    user1_response = e2e_client.post(
        "/api/users/",
        json={
            "username": "user1",
            "email": "user1@example.com",
            "name": "User 1",
        },
    )
    assert user1_response.status_code == 201
    user1_id = user1_response.json()["id"]
    
    user2_response = e2e_client.post(
        "/api/users/",
        json={
            "username": "user2",
            "email": "user2@example.com",
            "name": "User 2",
        },
    )
    assert user2_response.status_code == 201
    user2_id = user2_response.json()["id"]

    # Create password
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": owner_id,
            "name": "Multi-Share Password",
            "password": STRONG_PASSWORD,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Share with user 1
    share1_response = e2e_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": user1_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share1_response.status_code == 200

    # Share with user 2
    share2_response = e2e_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": user2_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share2_response.status_code == 200

    # Verify both users have access
    user1_access = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={user1_id}"
    )
    assert user1_access.status_code == 200

    user2_access = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={user2_id}"
    )
    assert user2_access.status_code == 200

    # Unshare with user 1 only
    unshare_response = e2e_client.delete(
        f"/api/passwords/{password_id}/share/{user1_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unshare_response.status_code == 200

    # Verify user 1 no longer has access but user 2 still does
    user1_no_access = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={user1_id}"
    )
    assert user1_no_access.status_code == 404

    user2_still_access = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={user2_id}"
    )
    assert user2_still_access.status_code == 200


def test_cannot_unshare_with_owner(e2e_client, setup, admin_token):
    """
    Test that owner cannot be unshared from their own password
    """
    owner_id = get_user_id_from_token(admin_token)

    # Create password
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": owner_id,
            "name": "Owner Password",
            "password": STRONG_PASSWORD,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Try to unshare owner from their own password
    unshare_response = e2e_client.delete(
        f"/api/passwords/{password_id}/share/{owner_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unshare_response.status_code == 400
    assert "owner" in unshare_response.json()["detail"].lower()


def test_cannot_share_with_nonexistent_user(e2e_client, setup, admin_token):
    """
    Test that sharing with a non-existent user returns 404
    """
    owner_id = get_user_id_from_token(admin_token)
    nonexistent_user_id = str(uuid4())

    # Create password
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": owner_id,
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Try to share with non-existent user
    share_response = e2e_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": nonexistent_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share_response.status_code == 404
    assert "does not exist" in share_response.json()["detail"]
