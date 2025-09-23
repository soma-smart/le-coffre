from uuid import UUID


def test_owner_has_full_access_to_password(e2e_client, setup):
    user_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"))

    # Create a password as the owner
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "user_id": user_id,
            "name": "Owner's Password",
            "password": "OwnerP@ssw0rd!",
        },
    )
    create_data = create_response.json()
    password_id = create_data["id"]

    # Ensure the owner can retrieve the password
    get_response = e2e_client.get(
        f"/api/passwords/{password_id}",
        params={"user_id": user_id},
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["name"] == "Owner's Password"

    # Ensure the owner can update the password
    update_response = e2e_client.put(
        f"/api/passwords/{password_id}",
        json={
            "user_id": user_id,
            "name": "Updated Owner's Password",
            "password": "NewOwnerP@ssw0rd!",
        },
    )
    assert update_response.status_code == 201

    # ensure the owner can delete the password
    delete_response = e2e_client.delete(
        f"/api/passwords/{password_id}",
        params={"user_id": user_id},
    )
    assert delete_response.status_code == 204
