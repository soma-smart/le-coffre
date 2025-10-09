import pytest


def test_vault_status_pending_after_setup(e2e_client):
    """Test that vault status is PENDING after initial setup"""
    # First create a vault
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 3,
            "threshold": 2,
        },
    )
    assert setup_response.status_code == 201
    
    # Check status is PENDING
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "PENDING"


def test_vault_status_after_validation(e2e_client):
    """Test that vault status changes after validation"""
    # First create a vault
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 3,
            "threshold": 2,
        },
    )
    assert setup_response.status_code == 201
    setup_id = setup_response.json()["setup_id"]
    
    # Validate the setup
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200
    
    # Check status is no longer PENDING
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    # After validation, vault should be LOCKED (since no session key is active)
    assert status_data["status"] in ["LOCKED", "SETUPED"]  # Allow either as it depends on session state


def test_cannot_setup_vault_when_already_validated(e2e_client):
    """Test that vault setup fails if vault is already validated"""
    # First create and validate a vault
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 3,
            "threshold": 2,
        },
    )
    assert setup_response.status_code == 201
    setup_id = setup_response.json()["setup_id"]
    
    # Validate the setup
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200
    
    # Try to setup a new vault - should fail
    setup_response2 = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    assert setup_response2.status_code == 400
    assert "already been created" in setup_response2.json()["detail"]