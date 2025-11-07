def test_can_list_passwords(e2e_client, setup, admin_token):
    folder = "Test Folder"

    for i in range(3):
        response = e2e_client.post(
            "/api/passwords",
            json={
                "name": f"Test Password {i}",
                "password": f"StrongP@ssw0rd{i}!",
                "folder": folder,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201

    list_response = e2e_client.get(
        f"/api/passwords/list/{folder}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    passwords = list_response.json()
    assert len(passwords) >= 3
    for i in range(3):
        assert any(p["name"] == f"Test Password {i}" for p in passwords)


def test_list_passwords_folder_not_found(e2e_client, setup, admin_token):
    non_existent_folder = "NonExistentFolder"

    response = e2e_client.get(
        f"/api/passwords/list/{non_existent_folder}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
