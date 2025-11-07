from uuid import uuid4
from utils import get_user_id_from_token, STRONG_PASSWORD
from fastapi.testclient import TestClient
from main import app


def test_share_password_workflow(e2e_client, setup, admin_token, sso_user_token):
    """
    Complete workflow: Create password → Share → Verify access → Unshare → Verify no access
    Uses a second user from SSO to test sharing functionality.

    NOTE: We use separate clients for admin and SSO user to avoid cookie interference,
    since cookies take priority over Authorization headers in our implementation.
    """
    shared_user_id = sso_user_token["user_id"]
    shared_user_token_str = sso_user_token["token"]

    # Create separate clients for admin and SSO user to avoid cookie interference
    admin_client = TestClient(app)
    sso_client = TestClient(app)

    # Step 1: Create a password as owner (admin)
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Shared Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Shared",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]
    assert create_response.json()["name"] == "Shared Test Password"

    # Step 2: Verify owner can read the password
    get_response = admin_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["password"] == STRONG_PASSWORD

    # Step 3: Verify SSO user cannot access password before sharing
    get_before_share = sso_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {shared_user_token_str}"},
    )
    assert get_before_share.status_code == 404

    # Step 4: Share password with SSO user
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": shared_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share_response.status_code == 201
    assert "successfully shared" in share_response.json()["message"]
    assert str(password_id) in share_response.json()["message"]
    assert str(shared_user_id) in share_response.json()["message"]

    # Step 5: Verify SSO user can now access the password
    get_after_share = sso_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {shared_user_token_str}"},
    )
    assert get_after_share.status_code == 200
    assert get_after_share.json()["name"] == "Shared Test Password"
    assert get_after_share.json()["password"] == STRONG_PASSWORD

    # Step 6: Unshare password from the SSO user
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{shared_user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unshare_response.status_code == 204

    # Step 7: Verify SSO user can no longer access the password
    get_after_unshare = sso_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {shared_user_token_str}"},
    )
    assert get_after_unshare.status_code == 404

    # Step 8: Verify owner still has access
    get_owner_final = admin_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_owner_final.status_code == 200
    assert get_owner_final.json()["password"] == STRONG_PASSWORD


def test_share_password_with_multiple_users(
    e2e_client, setup, admin_token, sso_user_token, second_sso_user_token
):
    """
    Test sharing a password with multiple SSO users
    """
    user1_id = sso_user_token["user_id"]
    user1_token = sso_user_token["token"]
    user2_id = second_sso_user_token["user_id"]
    user2_token = second_sso_user_token["token"]

    # Create separate clients for admin and each user to avoid cookie interference
    admin_client = TestClient(app)
    user1_client = TestClient(app)
    user2_client = TestClient(app)

    # Create password
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Multi-Share Password",
            "password": STRONG_PASSWORD,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Share with user 1
    share1_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": user1_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share1_response.status_code == 201

    # Share with user 2
    share2_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": user2_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share2_response.status_code == 201

    # Verify both users have access
    user1_access = user1_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert user1_access.status_code == 200
    assert user1_access.json()["password"] == STRONG_PASSWORD

    user2_access = user2_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert user2_access.status_code == 200
    assert user2_access.json()["password"] == STRONG_PASSWORD

    # Unshare with user 1 only
    unshare_response = admin_client.delete(
        f"/api/passwords/{password_id}/share/{user1_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unshare_response.status_code == 204

    # Verify user 1 no longer has access
    user1_no_access = user1_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert user1_no_access.status_code == 404

    # Verify user 2 still has access
    user2_still_access = user2_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert user2_still_access.status_code == 200
    assert user2_still_access.json()["password"] == STRONG_PASSWORD

    # Verify owner still has access
    owner_access = admin_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert owner_access.status_code == 200


def test_cannot_unshare_with_owner(e2e_client, setup, admin_token):
    """
    Test that owner cannot be unshared from their own password
    """
    owner_id = get_user_id_from_token(admin_token)

    # Create password
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Owner Password",
            "password": STRONG_PASSWORD,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
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
    nonexistent_user_id = str(uuid4())

    # Create password
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
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
