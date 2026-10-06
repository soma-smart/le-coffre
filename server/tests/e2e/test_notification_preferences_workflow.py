def test_notification_preferences_workflow(authenticated_admin_client, unauthenticated_client):
    """
    Notification preferences: off by default → turn vault lock/unlock emails on →
    read them back → turn one off → anonymous access refused.
    """
    client = authenticated_admin_client

    # === DEFAULT: every notification off ===
    response = client.get("/api/notifications/preferences")
    assert response.status_code == 200
    assert response.json() == {"notify_on_vault_lock": False, "notify_on_vault_unlock": False}

    # === OPT IN ===
    response = client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": True},
    )
    assert response.status_code == 200
    assert response.json() == {"notify_on_vault_lock": True, "notify_on_vault_unlock": True}

    response = client.get("/api/notifications/preferences")
    assert response.json() == {"notify_on_vault_lock": True, "notify_on_vault_unlock": True}

    # === OPT OUT OF ONE ===
    client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": False},
    )
    response = client.get("/api/notifications/preferences")
    assert response.json() == {"notify_on_vault_lock": True, "notify_on_vault_unlock": False}

    # === INCOMPLETE BODY ===
    response = client.put("/api/notifications/preferences", json={"notify_on_vault_lock": True})
    assert response.status_code == 422

    # === ANONYMOUS ===
    assert unauthenticated_client.get("/api/notifications/preferences").status_code == 401
    response = unauthenticated_client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": True},
    )
    assert response.status_code in (401, 403)
