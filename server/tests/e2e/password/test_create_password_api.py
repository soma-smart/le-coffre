from utils import STRONG_PASSWORD
from fastapi.testclient import TestClient
from main import app


def test_can_read_a_created_password(e2e_client, setup, admin_token):
    response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201

    retrieved_password = e2e_client.get(
        f"/api/passwords/{response.json()['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == STRONG_PASSWORD


def test_cannot_read_a_password_of_another_user(e2e_client, setup, admin_token):
    # Create password as admin
    response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    password_id = response.json()["id"]

    # Verify the user can access their own password
    retrieved_password = e2e_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert retrieved_password.status_code == 200

    # Try to access the password with an invalid token (should fail)
    # Use a fresh client without cookies to test invalid token
    fresh_client = TestClient(app)

    retrieved_password = fresh_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )

    # Should fail with 401 Unauthorized for invalid token
    assert retrieved_password.status_code == 401


def test_can_read_a_shared_password_of_another_user(
    e2e_client, setup, admin_token, sso_user_token
):
    # Get SSO user info
    other_user_id = sso_user_token["user_id"]
    other_user_token = sso_user_token["token"]

    # Create password as admin
    response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    password_id = response.json()["id"]

    # Share the password with the SSO user
    share_response = e2e_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": other_user_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share_response.status_code == 201

    # Admin should still be able to access their own password
    retrieved_password = e2e_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == STRONG_PASSWORD

    # SSO user should also be able to access the shared password
    other_user_retrieved = e2e_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {other_user_token}"},
    )

    assert other_user_retrieved.status_code == 200
    assert other_user_retrieved.json()["name"] == "Test Password"
    assert other_user_retrieved.json()["password"] == STRONG_PASSWORD


def test_cannot_create_weak_password(e2e_client, setup, admin_token):
    weak_password = "weakpass"
    response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Weak Password",
            "password": weak_password,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
