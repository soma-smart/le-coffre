import pytest


def test_can_lock_vault(e2e_client, vault_session_gateway):
    e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    lock_response = e2e_client.post(
        "/api/vault/lock",
    )

    assert lock_response.status_code == 200
    lock_data = lock_response.json()
    assert lock_data["message"] == "Vault locked successfully"

    with pytest.raises(ValueError):
        vault_session_gateway.get_decrypted_key()


def test_vault_lock_fails_when_already_locked(e2e_client, vault_session_gateway):
    e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    e2e_client.post(
        "/api/vault/lock",
    )

    second_lock_response = e2e_client.post(
        "/api/vault/lock",
    )

    assert second_lock_response.status_code == 400
