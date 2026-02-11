def test_vault_unlock_workflow(e2e_client, admin_token, unauthenticated_client):
    """
    Complete vault unlock workflow testing:
    - Setup vault with shares
    - Lock the vault
    - Test insufficient shares (PENDING_UNLOCK state)
    - Test clear pending shares
    - Test adding more shares after partial submission
    - Test invalid shares
    - Test successful unlock with sufficient shares
    - Test unlock without authentication
    - Test unlock with invalid token (no auth required)
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Step 1: Setup vault with 5 shares, threshold of 3
    threshold = 3
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": threshold,
        },
    )
    assert setup_response.status_code == 201

    setup_data = setup_response.json()
    shares = setup_data["shares"]
    share_secrets = [share["secret"] for share in shares]
    setup_id = setup_data["setup_id"]

    # Step 2: Validate setup
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Step 3: Lock the vault
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 200

    # Step 4: Submit insufficient shares (2 shares when threshold is 3)
    # This should create PENDING_UNLOCK state and return 202
    insufficient_shares = share_secrets[:2]
    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": insufficient_shares},
    )
    assert unlock_response.status_code == 202
    unlock_data = unlock_response.json()
    assert "More shares needed" in unlock_data["message"]

    # Step 5: Verify vault is in PENDING_UNLOCK state with timestamp
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "PENDING_UNLOCK"
    assert status_data["last_share_timestamp"] is not None

    # Step 6: Clear pending shares
    clear_response = e2e_client.delete("/api/vault/unlock/clear")
    assert clear_response.status_code == 200
    clear_data = clear_response.json()
    assert clear_data["message"] == "Pending shares cleared successfully"

    # Step 7: Verify vault is back to LOCKED state with no timestamp
    status_after_clear = e2e_client.get("/api/vault/status")
    assert status_after_clear.status_code == 200
    status_after_clear_data = status_after_clear.json()
    assert status_after_clear_data["status"] == "LOCKED"
    assert status_after_clear_data.get("last_share_timestamp") is None

    # Step 8: Submit insufficient shares again (1 share)
    unlock_response_2 = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": [share_secrets[0]]},
    )
    assert unlock_response_2.status_code == 202

    # Step 9: Add more shares to reach threshold (append 2 more to existing 1)
    # Total becomes 3 shares which should unlock
    additional_shares = share_secrets[1:3]
    unlock_response_3 = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": additional_shares},
    )
    assert unlock_response_3.status_code == 200
    unlock_data_3 = unlock_response_3.json()
    assert unlock_data_3["message"] == "Vault unlocked successfully"

    # Step 10: Verify vault is UNLOCKED
    status_unlocked = e2e_client.get("/api/vault/status")
    assert status_unlocked.status_code == 200
    assert status_unlocked.json()["status"] == "UNLOCKED"

    # Step 11: Lock vault again for more tests
    lock_response_2 = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response_2.status_code == 200

    # Step 12: Test with invalid shares (corrupted)
    # Even invalid shares return 202 (accepted but can't unlock)
    invalid_shares = [
        share.replace(share.split(":")[1], "wrongsecret") for share in share_secrets[:3]
    ]
    unlock_invalid = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": invalid_shares},
    )
    assert unlock_invalid.status_code == 202
    assert "More shares needed" in unlock_invalid.json()["message"]

    # Step 13: Clear invalid shares
    e2e_client.delete("/api/vault/unlock/clear")

    # Step 14: Test unlock without authentication (using unauthenticated client)
    valid_shares = share_secrets[:threshold]
    unlock_no_auth = unauthenticated_client.post(
        "/api/vault/unlock",
        json={"shares": valid_shares},
    )
    assert unlock_no_auth.status_code == 200
    assert unlock_no_auth.json()["message"] == "Vault unlocked successfully"

    # Step 15: Lock vault again
    lock_response_3 = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response_3.status_code == 200

    # Step 16: Test unlock with invalid token (should succeed since auth not required)
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    unlock_bad_token = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": valid_shares},
        headers=invalid_headers,
    )
    assert unlock_bad_token.status_code == 200
    assert unlock_bad_token.json()["message"] == "Vault unlocked successfully"
