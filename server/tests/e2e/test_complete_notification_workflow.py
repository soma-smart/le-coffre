"""
Complete End-to-End Notification Workflow.

1. Defaults: every notification off
2. Opt in to vault lock / unlock emails, read them back
3. Opt out of one
4. Validation: incomplete body refused
5. Anonymous access refused
6. A deleted user's preferences are removed with them
"""

import sqlite3

USER = {
    "username": "notified",
    "email": "notified@example.com",
    "name": "Notified User",
    "password": "SecurePassword123!",
}


def _preference_rows(database_path: str, user_id: str) -> int:
    with sqlite3.connect(database_path) as connection:
        (count,) = connection.execute(
            'SELECT COUNT(*) FROM "NotificationPreference" WHERE user_id = ?', (user_id.replace("-", ""),)
        ).fetchone()
    return count


def test_complete_notification_workflow(authenticated_admin_client, unauthenticated_client, client_factory, database):
    client = authenticated_admin_client

    # ===================================================================
    # PHASE 1: DEFAULTS
    # ===================================================================
    print("\n=== PHASE 1: DEFAULTS ===")

    response = client.get("/api/notifications/preferences")
    assert response.status_code == 200
    assert response.json() == {"notify_on_vault_lock": False, "notify_on_vault_unlock": False}
    print("✓ Every notification is off by default")

    # ===================================================================
    # PHASE 2: OPT IN
    # ===================================================================
    print("\n=== PHASE 2: OPT IN ===")

    response = client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": True},
    )
    assert response.status_code == 200
    assert response.json() == {"notify_on_vault_lock": True, "notify_on_vault_unlock": True}

    response = client.get("/api/notifications/preferences")
    assert response.json() == {"notify_on_vault_lock": True, "notify_on_vault_unlock": True}
    print("✓ Lock and unlock emails turned on and read back")

    # ===================================================================
    # PHASE 3: OPT OUT OF ONE
    # ===================================================================
    print("\n=== PHASE 3: OPT OUT OF ONE ===")

    client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": False},
    )
    response = client.get("/api/notifications/preferences")
    assert response.json() == {"notify_on_vault_lock": True, "notify_on_vault_unlock": False}
    print("✓ Unlock emails turned off, lock emails kept")

    # ===================================================================
    # PHASE 4: VALIDATION
    # ===================================================================
    print("\n=== PHASE 4: VALIDATION ===")

    response = client.put("/api/notifications/preferences", json={"notify_on_vault_lock": True})
    assert response.status_code == 422
    print("✓ Incomplete body refused")

    # ===================================================================
    # PHASE 5: ANONYMOUS ACCESS
    # ===================================================================
    print("\n=== PHASE 5: ANONYMOUS ACCESS ===")

    assert unauthenticated_client.get("/api/notifications/preferences").status_code == 401
    response = unauthenticated_client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": True},
    )
    assert response.status_code in (401, 403)
    print("✓ Anonymous read and update refused")

    # ===================================================================
    # PHASE 6: USER DELETION
    # ===================================================================
    print("\n=== PHASE 6: USER DELETION ===")

    response = client.post("/api/users/", json=USER)
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    user_client = client_factory()
    assert (
        user_client.post("/api/auth/login", json={"email": USER["email"], "password": USER["password"]}).status_code
        == 200
    )
    response = user_client.put(
        "/api/notifications/preferences",
        json={"notify_on_vault_lock": True, "notify_on_vault_unlock": True},
    )
    assert response.status_code == 200
    assert _preference_rows(database, user_id) == 1

    assert client.delete(f"/api/users/{user_id}").status_code in (200, 204)
    assert _preference_rows(database, user_id) == 0
    print("✓ The deleted user's preferences went with them")
