import pytest


def test_can_unlock_vault_with_valid_shares(e2e_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    threshold = 3
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": threshold,
        },
    )

    setup_data = setup_response.json()
    shares = setup_data["shares"]
    shares_to_use = shares[:threshold]

    e2e_client.post("/api/vault/lock", headers=headers)

    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in shares_to_use
            ]
        },
        headers=headers,
    )

    assert unlock_response.status_code == 200
    unlock_data = unlock_response.json()
    assert unlock_data["message"] == "Vault unlocked successfully"


def test_vault_unlock_fails_with_insufficient_real_shares(e2e_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )

    setup_data = setup_response.json()
    real_shares = setup_data["shares"]

    insufficient_shares = real_shares[:2]

    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in insufficient_shares
            ]
        },
        headers=headers,
    )

    assert unlock_response.status_code == 400
    unlock_data = unlock_response.json()
    assert "Failed to reconstruct secret from provided shares" in unlock_data["detail"]


def test_vault_unlock_fails_when_shares_given_are_wrong(e2e_client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )

    setup_data = setup_response.json()
    real_shares = setup_data["shares"]

    invalid_shares = [
        {"index": share["index"], "secret": "wrongsecret"} for share in real_shares[:3]
    ]

    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": invalid_shares},
        headers=headers,
    )

    assert unlock_response.status_code == 400
    unlock_data = unlock_response.json()
    assert "Failed to reconstruct secret from provided shares" in unlock_data["detail"]


def test_vault_unlock_fails_without_authentication(e2e_client):
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )

    setup_data = setup_response.json()
    shares = setup_data["shares"]
    shares_to_use = shares[:3]

    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in shares_to_use
            ]
        },
    )

    assert unlock_response.status_code == 422  # Missing authorization header


def test_vault_unlock_fails_with_invalid_token(e2e_client):
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )

    setup_data = setup_response.json()
    shares = setup_data["shares"]
    shares_to_use = shares[:3]

    headers = {"Authorization": "Bearer invalid_token"}

    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in shares_to_use
            ]
        },
        headers=headers,
    )

    assert unlock_response.status_code == 401  # Invalid token
