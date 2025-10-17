from uuid import UUID
import jwt

STRONG_PASSWORD = "StrongP@ssw0rd123"


def get_user_id_from_token(token: str) -> str:
    """Extract user_id from JWT token"""
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded["user_id"]


def test_can_read_a_created_password(e2e_client, setup):
    user_id = str(UUID("12345678-1234-5678-1234-567812345678"))

    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
    )

    assert response.status_code == 201

    retrieved_password = e2e_client.get(
        f"/api/passwords/{response.json()['id']}?user_id={user_id}"
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == STRONG_PASSWORD


def test_cannot_read_a_password_of_another_user(e2e_client, setup):
    user_id = str(UUID("87654321-4321-8765-4321-876543218765"))
    other_user = str(UUID("12345678-1234-5678-1234-567812345678"))

    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
    )

    retrieved_password = e2e_client.get(
        f"/api/passwords/{response.json()['id']}?user_id={other_user}"
    )

    assert retrieved_password.status_code == 404


def test_can_read_a_shared_password_of_another_user(e2e_client, setup, admin_token):
    user_id = get_user_id_from_token(admin_token)
    
    # Create the other user first
    other_user_response = e2e_client.post(
        "/api/users/",
        json={
            "username": "otheruser",
            "email": "other@example.com",
            "name": "Other User",
        },
    )
    assert other_user_response.status_code == 201
    other_user = other_user_response.json()["id"]

    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Test Password",
            "password": STRONG_PASSWORD,
        },
    )

    password_id = response.json()["id"]

    # Share the password using the new endpoint
    share_response = e2e_client.post(
        f"/api/passwords/{password_id}/share",
        json={"user_id": other_user},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert share_response.status_code == 200

    retrieved_password = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={other_user}"
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == STRONG_PASSWORD


def test_cannot_create_weak_password(e2e_client, setup):
    user_id = str(UUID("12345678-1234-5678-1234-567812345678"))
    weak_password = "weakpass"
    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Weak Password",
            "password": weak_password,
        },
    )

    assert response.status_code == 400
