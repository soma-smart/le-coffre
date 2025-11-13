from uuid import UUID


def test_can_delete_password(authenticated_admin_client, setup):
    folder = "Delete Test Folder"

    # Create a password to delete
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Password To Delete",
            "password": "StrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Delete the created password
    delete_response = authenticated_admin_client.delete(
        f"/api/passwords/{password_id}",
    )
    assert delete_response.status_code == 204


def test_delete_nonexistent_password(authenticated_admin_client, setup):
    nonexistent_password_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7"))

    # Attempt to delete a non-existent password
    delete_response = authenticated_admin_client.delete(
        f"/api/passwords/{nonexistent_password_id}",
    )
    assert delete_response.status_code == 404


def test_delete_password_requires_authentication(
    authenticated_admin_client, unauthenticated_client, setup
):
    folder = "Auth Test Folder"

    # Create a password
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

    # Attempt to delete the password without authentication
    delete_response = unauthenticated_client.delete(
        f"/api/passwords/{password_id}",
    )
    assert delete_response.status_code == 401  # Unauthorized
