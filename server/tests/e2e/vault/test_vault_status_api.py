def test_can_access_vault_status(e2e_client):
    # Initial status should be NOT_SETUP
    not_setup_response = e2e_client.get("/api/vault/status")

    assert not_setup_response.status_code == 200
    not_setup_data = not_setup_response.json()

    assert not_setup_data["status"] == "NOT_SETUP"

    # Setup to have UNLOCKED status
    e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    unlocked_response = e2e_client.get("/api/vault/status")
    assert unlocked_response.status_code == 200
    unlocked_data = unlocked_response.json()
    assert unlocked_data["status"] == "UNLOCKED"

    # Lock the vault to have LOCKED status
    e2e_client.post("/api/vault/lock")
    locked_response = e2e_client.get("/api/vault/status")
    assert locked_response.status_code == 200
    locked_data = locked_response.json()
    assert locked_data["status"] == "LOCKED"
