from uuid import UUID


def test_can_list_passwords(e2e_client, setup):
    user_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"))
    folder = "Test Folder"

    for i in range(3):
        response = e2e_client.post(
            "/api/passwords",
            json={
                "user_id": user_id,
                "name": f"Test Password {i}",
                "password": f"StrongP@ssw0rd{i}!",
                "folder": folder,
            },
        )
        assert response.status_code == 201

    list_response = e2e_client.get(f"/api/passwords/list/{folder}?user_id={user_id}")
    assert list_response.status_code == 200
    passwords = list_response.json()
    assert len(passwords) >= 3
    for i in range(3):
        assert any(p["name"] == f"Test Password {i}" for p in passwords)


def test_list_passwords_folder_not_found(e2e_client, setup):
    user_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6"))
    non_existent_folder = "NonExistentFolder"

    response = e2e_client.get(
        f"/api/passwords/list/{non_existent_folder}?user_id={user_id}"
    )
    assert response.status_code == 404
