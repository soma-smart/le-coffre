def test_can_access_vault_status(e2e_client, admin_token):
    # Initial status should be NOT_SETUP
    not_setup_response = e2e_client.get("/api/vault/status")

    assert not_setup_response.status_code == 200
    not_setup_data = not_setup_response.json()

    assert not_setup_data["status"] == "NOT_SETUP"

    # Setup vault - will be in PENDING status but with session key unlocked
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    assert setup_response.status_code == 201
    setup_id = setup_response.json()["setup_id"]
    
    # Check status - should be UNLOCKED because session key is stored
    unlocked_response = e2e_client.get("/api/vault/status")
    assert unlocked_response.status_code == 200
    assert unlocked_response.json()["status"] == "UNLOCKED"
    
    # Validate to complete setup 
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200
    
    # After validation, should still be UNLOCKED
    setuped_response = e2e_client.get("/api/vault/status")
    assert setuped_response.status_code == 200
    setuped_data = setuped_response.json()
    assert setuped_data["status"] == "UNLOCKED"
