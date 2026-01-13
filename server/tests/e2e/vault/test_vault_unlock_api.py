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
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Lock the vault first
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 200

    # Now unlock it with shares - no authentication required
    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in shares_to_use
            ]
        },
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
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Lock the vault first
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 200

    insufficient_shares = real_shares[:2]

    # No authentication required for unlock
    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in insufficient_shares
            ]
        },
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
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Lock the vault first
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 200

    invalid_shares = [
        {"index": share["index"], "secret": "wrongsecret"} for share in real_shares[:3]
    ]

    # No authentication required for unlock
    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={"shares": invalid_shares},
    )

    assert unlock_response.status_code == 400
    unlock_data = unlock_response.json()
    assert "Failed to reconstruct secret from provided shares" in unlock_data["detail"]


def test_vault_unlock_succeeds_without_authentication(
    e2e_client, admin_token, unauthenticated_client
):
    """Test that vault unlock works without authentication since it's needed before login"""
    headers = {"Authorization": f"Bearer {admin_token}"}

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
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Lock the vault first
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 200

    # Unlock without authentication should succeed
    unlock_response = unauthenticated_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in shares_to_use
            ]
        },
    )

    assert unlock_response.status_code == 200
    unlock_data = unlock_response.json()
    assert unlock_data["message"] == "Vault unlocked successfully"


def test_vault_unlock_succeeds_with_any_token(e2e_client, admin_token):
    """Test that vault unlock works even with invalid token since auth is not required"""
    headers = {"Authorization": f"Bearer {admin_token}"}

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
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Lock the vault first
    lock_response = e2e_client.post("/api/vault/lock", headers=headers)
    assert lock_response.status_code == 200

    invalid_headers = {"Authorization": "Bearer invalid_token"}

    # Unlock with invalid token should succeed since auth is not checked
    unlock_response = e2e_client.post(
        "/api/vault/unlock",
        json={
            "shares": [
                {"index": share["index"], "secret": share["secret"]}
                for share in shares_to_use
            ]
        },
        headers=invalid_headers,
    )

    assert unlock_response.status_code == 200
    unlock_data = unlock_response.json()
    assert unlock_data["message"] == "Vault unlocked successfully"
