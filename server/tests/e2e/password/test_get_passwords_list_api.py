def test_can_list_passwords(authenticated_admin_client, setup, admin_personal_group_id):
    folder = "Test Folder"

    for i in range(3):
        response = authenticated_admin_client.post(
            "/api/passwords",
            json={
                "name": f"Test Password {i}",
                "password": f"StrongP@ssw0rd{i}!",
                "folder": folder,
                "group_id": admin_personal_group_id,
            },
        )
        assert response.status_code == 201

    list_response = authenticated_admin_client.get(
        f"/api/passwords/list?folder={folder}",
    )
    assert list_response.status_code == 200
    passwords = list_response.json()
    assert len(passwords) >= 3
    for i in range(3):
        password = next(
            (p for p in passwords if p["name"] == f"Test Password {i}"), None
        )
        assert password is not None
        assert password["group_id"] == admin_personal_group_id


def test_list_passwords_folder_not_found(authenticated_admin_client, setup):
    non_existent_folder = "NonExistentFolder"

    response = authenticated_admin_client.get(
        f"/api/passwords/list?folder={non_existent_folder}",
    )
    assert response.status_code == 404
