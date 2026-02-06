from utils import STRONG_PASSWORD


def test_list_password_events_workflow(
    client_factory, setup, configured_sso, sso_user_token
):
    """
    Complete workflow: Create password → Get password → Update password → List events

    Verifies that:
    1. Events are recorded for password operations
    2. User with READ permission can list events
    3. Events are returned in reverse chronological order
    4. Event filtering works correctly
    """
    # Create separate clients for admin and SSO user
    admin_client = client_factory()
    sso_client = client_factory()

    # Register and login admin
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }
    admin_client.post("/api/auth/register-admin", json=admin_data)
    admin_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin"},
    )

    # Login SSO user
    sso_client.cookies.set("access_token", sso_user_token["token"])

    # Get SSO user's personal group ID
    sso_user_response = sso_client.get("/api/users/me")
    assert sso_user_response.status_code == 200
    sso_user_group_id = sso_user_response.json()["personal_group_id"]

    # Get admin's personal group ID
    admin_response = admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]

    # Step 1: Create a password (generates password.created event)
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Work",
            "group_id": admin_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Step 2: Access the password (generates password.accessed event)
    get_response = admin_client.get(f"/api/passwords/{password_id}")
    assert get_response.status_code == 200

    # Step 3: Update the password (generates password.updated event)
    update_response = admin_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Work",
        },
    )
    assert update_response.status_code == 201

    # Step 4: Share with SSO user (generates password.shared event)
    share_response = admin_client.post(
        f"/api/passwords/{password_id}/share",
        json={"group_id": sso_user_group_id},
    )
    assert share_response.status_code == 201

    # Step 5: List all events for the password (admin has access)
    events_response = admin_client.get(f"/api/passwords/{password_id}/events")
    assert events_response.status_code == 200

    events = events_response.json()["events"]
    assert len(events) >= 4  # At least created, accessed, updated, shared

    # Verify event types are present
    event_types = [event["event_type"] for event in events]
    assert "PasswordCreatedEvent" in event_types
    assert "PasswordAccessedEvent" in event_types
    assert "PasswordUpdatedEvent" in event_types
    assert "PasswordSharedEvent" in event_types

    # Verify events are in reverse chronological order (most recent first)
    for i in range(len(events) - 1):
        assert events[i]["occurred_on"] >= events[i + 1]["occurred_on"]

    # Verify each event has required fields
    for event in events:
        assert "event_id" in event
        assert "event_type" in event
        assert "occurred_on" in event
        assert "actor_user_id" in event
        assert "event_data" in event

    # Step 6: Filter events by event type
    filtered_response = admin_client.get(
        f"/api/passwords/{password_id}/events",
        params={"event_type": ["PasswordCreatedEvent", "PasswordUpdatedEvent"]},
    )
    assert filtered_response.status_code == 200
    filtered_events = filtered_response.json()["events"]
    filtered_types = [event["event_type"] for event in filtered_events]
    assert all(
        event_type in ["PasswordCreatedEvent", "PasswordUpdatedEvent"]
        for event_type in filtered_types
    )
    assert "PasswordAccessedEvent" not in filtered_types

    # Step 7: Verify SSO user (with READ permission) can also list events
    sso_events_response = sso_client.get(f"/api/passwords/{password_id}/events")
    assert sso_events_response.status_code == 200
    sso_events = sso_events_response.json()["events"]
    assert len(sso_events) >= 4

    # Step 8: Verify user without access cannot list events
    unauthorized_client = client_factory()
    unauthorized_client.post(
        "/api/auth/register-admin",
        json={
            "email": "unauthorized@example.com",
            "password": "password",
            "display_name": "Unauthorized User",
        },
    )
    unauthorized_client.post(
        "/api/auth/login",
        json={"email": "unauthorized@example.com", "password": "password"},
    )

    unauthorized_response = unauthorized_client.get(
        f"/api/passwords/{password_id}/events"
    )
    # User without access should get 401 (vault not unlocked) or 404 (not found for security)
    assert unauthorized_response.status_code in [401, 404]
