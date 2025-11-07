def test_owner_has_full_access_to_password(e2e_client, setup, admin_token):
    # Create a password as the owner
    create_response = e2e_client.post(
        "/api/passwords",
        json={
            "name": "Owner's Password",
            "password": "OwnerP@ssw0rd!",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    create_data = create_response.json()
    password_id = create_data["id"]

    # Ensure the owner can retrieve the password
    get_response = e2e_client.get(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["name"] == "Owner's Password"

    # Ensure the owner can update the password
    update_response = e2e_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Owner's Password",
            "password": "NewOwnerP@ssw0rd!",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 201

    # ensure the owner can delete the password
    delete_response = e2e_client.delete(
        f"/api/passwords/{password_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204
