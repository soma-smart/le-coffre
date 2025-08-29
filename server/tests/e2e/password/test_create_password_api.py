import pytest
from uuid import UUID


def test_can_read_a_created_password(e2e_client, setup):
    user_id = str(UUID("12345678-1234-5678-1234-567812345678"))

    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Test Password",
            "password": "secret123",
        },
    )

    assert response.status_code == 201

    retrieved_password = e2e_client.get(
        f"/api/passwords/{response.json()['id']}?user_id={user_id}"
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == "secret123"


def test_cannot_read_a_password_of_another_user(e2e_client, setup):
    user_id = str(UUID("87654321-4321-8765-4321-876543218765"))
    other_user = str(UUID("12345678-1234-5678-1234-567812345678"))

    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Test Password",
            "password": "secret123",
        },
    )

    retrieved_password = e2e_client.get(
        f"/api/passwords/{response.json()['id']}?user_id={other_user}"
    )

    assert retrieved_password.status_code == 403


def test_can_read_a_shared_password_of_another_user(e2e_client, setup):
    user_id = str(UUID("87654321-4321-8765-4321-876543218765"))
    other_user = str(UUID("12345678-1234-5678-1234-567812345678"))

    response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Test Password",
            "password": "secret123",
            "shared_with": [other_user],
        },
    )

    password_id = response.json()["id"]

    e2e_client.post(
        f"/api/{password_id}/share",
        json={"from_id": user_id, "to_id": other_user},
    )

    retrieved_password = e2e_client.get(
        f"/api/passwords/{password_id}?user_id={other_user}"
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == "secret123"
