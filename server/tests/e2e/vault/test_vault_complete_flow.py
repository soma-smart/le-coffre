import pytest


def test_complete_vault_setup_flow(e2e_client):
    """
    Test the complete vault setup flow step by step:
    setup => check return => check status => setup => check return => check status 
    => validate => check return => check status => setup => check return => check status
    """
    
    # Step 1: Initial setup
    setup_response1 = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 3, "threshold": 2},
    )
    
    # Check return
    assert setup_response1.status_code == 201
    setup_data1 = setup_response1.json()
    assert "setup_id" in setup_data1
    assert "shares" in setup_data1
    assert len(setup_data1["shares"]) == 3
    setup_id1 = setup_data1["setup_id"]
    
    # Check status
    status_response1 = e2e_client.get("/api/vault/status")
    assert status_response1.status_code == 200
    assert status_response1.json()["status"] == "PENDING"
    
    # Step 2: Setup again (should be allowed in PENDING state)
    setup_response2 = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 5, "threshold": 3},
    )
    
    # Check return
    assert setup_response2.status_code == 201
    setup_data2 = setup_response2.json()
    assert "setup_id" in setup_data2
    assert "shares" in setup_data2
    assert len(setup_data2["shares"]) == 5
    setup_id2 = setup_data2["setup_id"]
    assert setup_id2 != setup_id1  # Should be different
    
    # Check status (still PENDING)
    status_response2 = e2e_client.get("/api/vault/status")
    assert status_response2.status_code == 200
    assert status_response2.json()["status"] == "PENDING"
    
    # Step 3: Validate setup with latest setup_id
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id2},
    )
    
    # Check return
    assert validate_response.status_code == 200
    validate_data = validate_response.json()
    assert validate_data["message"] == "Vault setup completed successfully"
    
    # Check status (should no longer be PENDING)
    status_response3 = e2e_client.get("/api/vault/status")
    assert status_response3.status_code == 200
    status = status_response3.json()["status"]
    assert status in ["LOCKED", "SETUPED"]  # Vault is now complete but locked
    
    # Step 4: Try to setup again (should fail now that vault is validated)
    setup_response3 = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 4, "threshold": 2},
    )
    
    # Check return (should fail)
    assert setup_response3.status_code == 400
    error_data = setup_response3.json()
    assert "already been created" in error_data["detail"]
    
    # Check status (should remain the same)
    status_response4 = e2e_client.get("/api/vault/status")
    assert status_response4.status_code == 200
    assert status_response4.json()["status"] == status  # Same as before


def test_validate_with_wrong_setup_id_fails(e2e_client):
    """Test that validation fails with wrong setup_id"""
    # Setup vault first
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 3, "threshold": 2},
    )
    assert setup_response.status_code == 201
    
    # Try to validate with wrong setup_id
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": "wrong-setup-id"},
    )
    
    assert validate_response.status_code == 400
    assert "Invalid setup ID" in validate_response.json()["detail"]


def test_validate_already_validated_vault_fails(e2e_client):
    """Test that validation fails if vault is already validated"""
    # Setup and validate vault
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 3, "threshold": 2},
    )
    setup_id = setup_response.json()["setup_id"]
    
    validate_response1 = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response1.status_code == 200
    
    # Try to validate again
    validate_response2 = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    
    assert validate_response2.status_code == 400
    assert "not in pending state" in validate_response2.json()["detail"]