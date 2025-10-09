import pytest


def test_can_lock_vault(e2e_client, setup, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Vault is already unlocked after setup, just lock it
    lock_response = e2e_client.post(
        "/api/vault/lock",
        headers=headers,
    )

    assert lock_response.status_code == 200, lock_response.text
    lock_data = lock_response.json()
    assert lock_data["message"] == "Vault locked successfully"


def test_vault_lock_fails_when_already_locked(e2e_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    e2e_client.post(
        "/api/vault/lock",
        headers=headers,
    )

    second_lock_response = e2e_client.post(
        "/api/vault/lock",
        headers=headers,
    )

    assert second_lock_response.status_code == 400


def test_vault_lock_fails_without_authentication(e2e_client, setup):
    lock_response = e2e_client.post("/api/vault/lock")
    assert lock_response.status_code == 422


def test_vault_lock_fails_with_invalid_token(e2e_client, setup):
    headers = {"Authorization": "Bearer invalid_token"}
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 401
