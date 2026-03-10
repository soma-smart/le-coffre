def test_vault_workflow(e2e_client, client_factory):
    """
    Complete vault workflow:
    NOT_SETUP → setup (x2) → validate (wrong id fails) → validate (correct id) →
    setup again fails → validate again fails → lock → lock again fails →
    lock without auth fails → PENDING_UNLOCK → clear → incremental unlock →
    UNLOCKED → lock → invalid shares → clear
    """
    unauthenticated_client = client_factory()

    # === STATUS: NOT_SETUP ===
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "NOT_SETUP"

    # === REGISTER AND LOGIN ADMIN ===
    e2e_client.post(
        "/api/auth/register-admin",
        json={
            "email": "admin@example.com",
            "password": "admin",
            "display_name": "System Administrator",
        },
    )
    login_response = e2e_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin"},
    )
    assert login_response.status_code == 200
    e2e_client.refresh_csrf_token()

    # === SETUP PHASE (first setup) ===
    setup_response1 = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 3, "threshold": 2},
    )
    assert setup_response1.status_code == 201
    setup_data1 = setup_response1.json()
    assert "setup_id" in setup_data1
    assert "shares" in setup_data1
    assert len(setup_data1["shares"]) == 3
    setup_id1 = setup_data1["setup_id"]

    # Status should be UNLOCKED (session key stored during setup)
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "UNLOCKED"

    # === SETUP PHASE (second setup – re-setup allowed before validation) ===
    nb_shares = 5
    threshold = 3
    setup_response2 = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": nb_shares, "threshold": threshold},
    )
    assert setup_response2.status_code == 201
    setup_data2 = setup_response2.json()
    assert "setup_id" in setup_data2
    assert "shares" in setup_data2
    assert len(setup_data2["shares"]) == nb_shares
    setup_id2 = setup_data2["setup_id"]
    assert setup_id2 != setup_id1
    shares = setup_data2["shares"]
    share_secrets = [share["secret"] for share in shares]

    # Status still UNLOCKED
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "UNLOCKED"

    # === VALIDATE PHASE: wrong setup_id must fail ===
    validate_wrong = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": "550e8400-e29b-41d4-a716-446655440000"},
    )
    assert validate_wrong.status_code == 400
    assert "Invalid setup ID" in validate_wrong.json()["detail"]

    # === VALIDATE PHASE: correct setup_id ===
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id2},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["message"] == "Vault setup completed successfully"

    # Status still UNLOCKED after validation
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "UNLOCKED"

    # === SETUP AFTER VALIDATION: must fail ===
    setup_after_validation = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 4, "threshold": 2},
    )
    assert setup_after_validation.status_code == 400
    assert "already been created" in setup_after_validation.json()["detail"]

    # Status remains UNLOCKED
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "UNLOCKED"

    # === VALIDATE AGAIN: must fail ===
    validate_again = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id2},
    )
    assert validate_again.status_code == 400
    assert "not in pending state" in validate_again.json()["detail"]

    # === LOCK PHASE ===
    lock_response = e2e_client.post("/api/vault/lock")
    assert lock_response.status_code == 200
    assert lock_response.json()["message"] == "Vault locked successfully"

    # === LOCK AGAIN: must fail ===
    lock_again_response = e2e_client.post("/api/vault/lock")
    assert lock_again_response.status_code == 400

    # === LOCK WITHOUT AUTH: must fail ===
    lock_no_auth = unauthenticated_client.post("/api/vault/lock")
    assert lock_no_auth.status_code == 401

    # Status is LOCKED
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "LOCKED"

    # === UNLOCK PHASE: insufficient shares → PENDING_UNLOCK ===
    insufficient_shares = share_secrets[:2]
    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": insufficient_shares},
    )
    assert unlock_response.status_code == 202
    assert "More shares needed" in unlock_response.json()["message"]

    # Status is PENDING_UNLOCK with a timestamp
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "PENDING_UNLOCK"
    assert status_data["last_share_timestamp"] is not None

    # === CLEAR PENDING SHARES ===
    clear_response = e2e_client.delete("/api/vault/unlock/clear")
    assert clear_response.status_code == 200
    assert clear_response.json()["message"] == "Pending shares cleared successfully"

    # Status back to LOCKED with no timestamp
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "LOCKED"
    assert status_data.get("last_share_timestamp") is None

    # === INCREMENTAL UNLOCK: submit 1 share then 2 more to reach threshold ===
    unlock_partial = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": [share_secrets[0]]},
    )
    assert unlock_partial.status_code == 202

    unlock_final = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": share_secrets[1:3]},
    )
    assert unlock_final.status_code == 200
    assert unlock_final.json()["message"] == "Vault unlocked successfully"

    # Status is UNLOCKED
    status_response = e2e_client.get("/api/vault/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "UNLOCKED"

    # === LOCK AGAIN FOR FURTHER TESTS ===
    e2e_client.post("/api/vault/lock")

    # === INVALID SHARES: corrupted secrets ===
    invalid_shares = [share.replace(share.split(":")[1], "wrongsecret") for share in share_secrets[:3]]
    unlock_invalid = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": invalid_shares},
    )
    assert unlock_invalid.status_code == 202
    assert "More shares needed" in unlock_invalid.json()["message"]

    # Clear invalid shares
    e2e_client.delete("/api/vault/unlock/clear")
