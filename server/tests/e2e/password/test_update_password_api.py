from uuid import UUID


def test_can_update_password(authenticated_admin_client, setup):
    folder = "Update Test Folder"

    # Create a password to update
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Password To Update",
            "password": "StrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Update the created password
    update_response = authenticated_admin_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Password Name",
            "password": "NewStrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert update_response.status_code == 201


def test_update_nonexistent_password(authenticated_admin_client, setup):
    nonexistent_password_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7"))

    # Attempt to update a non-existent password
    update_response = authenticated_admin_client.put(
        f"/api/passwords/{nonexistent_password_id}",
        json={
            "name": "Updated Password Name",
            "password": "NewStrongP@ssw0rd!",
            "folder": "folder",
        },
    )
    assert update_response.status_code == 404


def test_update_password_requires_authentication(
    authenticated_admin_client, unauthenticated_client, setup
):
    folder = "Auth Test Folder"

    # Create a password with a valid user
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Password For Auth Test",
            "password": "StrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Attempt to update the password without authentication
    update_response = unauthenticated_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Password Name",
            "password": "NewStrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert update_response.status_code == 401  # Unauthorized
