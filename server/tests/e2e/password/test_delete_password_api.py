from uuid import UUID


def test_can_delete_password(e2e_client, setup):
    user_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"))
    folder = "Delete Test Folder"

    # Create a password to delete
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Password To Delete",
            "password": "StrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Delete the created password
    delete_response = e2e_client.delete(
        f"/api/passwords/{password_id}",
        params={"user_id": user_id},
    )
    assert delete_response.status_code == 204


def test_delete_nonexistent_password(e2e_client, setup):
    user_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"))
    nonexistent_password_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7"))

    # Attempt to delete a non-existent password
    delete_response = e2e_client.delete(
        f"/api/passwords/{nonexistent_password_id}",
        params={"user_id": user_id},
    )
    assert delete_response.status_code == 404


def test_delete_password_invalid_user(e2e_client, setup):
    valid_user_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"))
    invalid_user_id = str(UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e8"))
    folder = "Invalid User Test Folder"

    # Create a password with a valid user
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": valid_user_id,
            "name": "Password For Invalid User Test",
            "password": "StrongP@ssw0rd!",
            "folder": folder,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Attempt to delete the password with an invalid user
    delete_response = e2e_client.delete(
        f"/api/passwords/{password_id}",
        params={"user_id": invalid_user_id},
    )
    assert delete_response.status_code == 404
