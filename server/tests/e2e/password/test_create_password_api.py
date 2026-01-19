from utils import STRONG_PASSWORD


def test_can_read_a_created_password(
    authenticated_admin_client, setup, admin_personal_group_id
):
    response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
            "group_id": admin_personal_group_id,
        },
    )

    assert response.status_code == 201

    retrieved_password = authenticated_admin_client.get(
        f"/api/passwords/{response.json()['id']}",
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == STRONG_PASSWORD


def test_cannot_read_a_password_of_another_user(
    authenticated_admin_client,
    unauthenticated_client,
    setup,
    admin_personal_group_id,
):
    # Create password as admin
    response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
            "group_id": admin_personal_group_id,
        },
    )
    assert response.status_code == 201
    password_id = response.json()["id"]

    # Verify the user can access their own password
    retrieved_password = authenticated_admin_client.get(
        f"/api/passwords/{password_id}",
    )
    assert retrieved_password.status_code == 200

    # Try to access the password without authentication (should fail)
    retrieved_password = unauthenticated_client.get(
        f"/api/passwords/{password_id}",
    )

    # Should fail with 401 Unauthorized
    assert retrieved_password.status_code == 401


def test_can_read_a_shared_password_of_another_user(
    authenticated_admin_client,
    authenticated_sso_user_client,
    setup,
    sso_user_token,
    admin_personal_group_id,
    sso_user_personal_group_id,
):
    # Create password as admin
    response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
            "group_id": admin_personal_group_id,
        },
    )

    password_id = response.json()["id"]

    # Share the password with the SSO user's personal group
    share_response = authenticated_admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_user_personal_group_id},
    )
    assert share_response.status_code == 201

    # Admin should still be able to access their own password
    retrieved_password = authenticated_admin_client.get(
        f"/api/passwords/{password_id}",
    )

    assert retrieved_password.status_code == 200
    assert retrieved_password.json()["name"] == "Test Password"
    assert retrieved_password.json()["password"] == STRONG_PASSWORD

    # SSO user should also be able to access the shared password
    other_user_retrieved = authenticated_sso_user_client.get(
        f"/api/passwords/{password_id}",
    )

    assert other_user_retrieved.status_code == 200
    assert other_user_retrieved.json()["name"] == "Test Password"
    assert other_user_retrieved.json()["password"] == STRONG_PASSWORD


def test_cannot_create_weak_password(
    authenticated_admin_client, setup, admin_personal_group_id
):
    weak_password = "weakpass"
    response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Weak Password",
            "password": weak_password,
            "group_id": admin_personal_group_id,
        },
    )

    assert response.status_code == 400
