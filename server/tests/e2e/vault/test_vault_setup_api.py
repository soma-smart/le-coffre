import pytest


def test_can_create_the_vault(e2e_client):
    response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )

    assert response.status_code == 201
    response_data = response.json()

    # Check that we have a setup_id and shares in the response
    assert "setup_id" in response_data
    assert "shares" in response_data
    assert isinstance(response_data["setup_id"], str)
    assert len(response_data["setup_id"]) > 20  # UUID should be longer than 20 chars

    shares = response_data["shares"]
    assert len(shares) == 5

    for share in shares:
        assert "index" in share and isinstance(share["index"], int)
        assert (
            "secret" in share
            and isinstance(share["secret"], str)
            and len(share["secret"]) > 20
        )
        int(share["secret"], 16)


def test_can_validate_vault_setup(e2e_client):
    # First create a vault
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 3,
            "threshold": 2,
        },
    )
    
    assert setup_response.status_code == 201
    setup_data = setup_response.json()
    setup_id = setup_data["setup_id"]

    # Then validate the setup
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={
            "setup_id": setup_id,
        },
    )

    assert validate_response.status_code == 200
    validate_data = validate_response.json()
    assert validate_data["message"] == "Vault setup completed successfully"


def test_validate_with_invalid_setup_id_fails(e2e_client):
    response = e2e_client.post(
        "/api/vault/validate-setup",
        json={
            "setup_id": "invalid-setup-id",
        },
    )

    assert response.status_code == 400
    assert "Invalid setup ID" in response.json()["detail"]


def test_can_setup_vault_again_when_pending(e2e_client):
    # First create a vault
    setup_response1 = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 3,
            "threshold": 2,
        },
    )
    assert setup_response1.status_code == 201

    # Should be able to setup again while in pending state
    setup_response2 = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    assert setup_response2.status_code == 201
    
    # Setup IDs should be different
    setup_id1 = setup_response1.json()["setup_id"]
    setup_id2 = setup_response2.json()["setup_id"]
    assert setup_id1 != setup_id2
