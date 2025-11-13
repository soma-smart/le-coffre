def test_can_lock_vault(authenticated_admin_client, setup):
    # Vault is already unlocked after setup, just lock it
    lock_response = authenticated_admin_client.post(
        "/api/vault/lock",
    )

    assert lock_response.status_code == 200, lock_response.text
    lock_data = lock_response.json()
    assert lock_data["message"] == "Vault locked successfully"


def test_vault_lock_fails_when_already_locked(authenticated_admin_client):
    authenticated_admin_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    authenticated_admin_client.post(
        "/api/vault/lock",
    )

    second_lock_response = authenticated_admin_client.post(
        "/api/vault/lock",
    )

    assert second_lock_response.status_code == 400


def test_vault_lock_fails_without_authentication(unauthenticated_client, setup):
    lock_response = unauthenticated_client.post("/api/vault/lock")
    assert lock_response.status_code == 401  # Unauthorized
