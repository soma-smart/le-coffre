def test_event_logs_workflow(
    authenticated_admin_client, setup, admin_personal_group_id
):
    """
    Complete workflow testing audit event logging:
    1. Verify initial state (empty or only setup events)
    2. Create a password → should emit PasswordCreatedEvent
    3. Verify event is logged with correct details
    4. Update the password → should emit PasswordUpdatedEvent
    5. Verify update event is logged
    6. Delete the password → should emit PasswordDeletedEvent
    7. Verify delete event is logged
    8. Verify events are chronologically ordered
    """

    # Step 1: Get initial event count
    initial_events_response = authenticated_admin_client.get("/api/events")
    assert initial_events_response.status_code == 200
    initial_events = initial_events_response.json()["events"]
    initial_count = len(initial_events)

    # Step 2: Create a password (should emit PasswordCreatedEvent)
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "Test Password for Audit",
            "password": "SecureP@ss123",
            "folder": "Audit Test",
            "group_id": admin_personal_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Step 3: Verify PasswordCreatedEvent was logged
    after_create_response = authenticated_admin_client.get("/api/events")
    assert after_create_response.status_code == 200
    after_create_events = after_create_response.json()["events"]
    assert len(after_create_events) == initial_count + 1, (
        "Expected one new event after password creation"
    )

    # Find the most recent event (should be PasswordCreatedEvent)
    latest_event = after_create_events[-1]
    assert latest_event["event_type"] == "PasswordCreatedEvent"
    assert latest_event["priority"] == "HIGH"
    assert "event_id" in latest_event
    assert "occurred_on" in latest_event

    # Step 4: Update the password (should emit PasswordUpdatedEvent)
    update_response = authenticated_admin_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Test Password",
            "password": "NewSecureP@ss456",
            "folder": "Updated Folder",
        },
    )
    assert update_response.status_code == 201

    # Step 5: Verify PasswordUpdatedEvent was logged
    after_update_response = authenticated_admin_client.get("/api/events")
    assert after_update_response.status_code == 200
    after_update_events = after_update_response.json()["events"]
    assert len(after_update_events) == initial_count + 2, (
        "Expected two new events after password update"
    )

    # Verify the update event
    update_event = after_update_events[-1]
    assert update_event["event_type"] == "PasswordUpdatedEvent"
    assert update_event["priority"] == "MEDIUM"

    # Step 6: Delete the password (should emit PasswordDeletedEvent)
    delete_response = authenticated_admin_client.delete(f"/api/passwords/{password_id}")
    assert delete_response.status_code == 204

    # Step 7: Verify PasswordDeletedEvent was logged
    after_delete_response = authenticated_admin_client.get("/api/events")
    assert after_delete_response.status_code == 200
    after_delete_events = after_delete_response.json()["events"]
    assert len(after_delete_events) == initial_count + 3, (
        "Expected three new events after password deletion"
    )

    # Verify the delete event
    delete_event = after_delete_events[-1]
    assert delete_event["event_type"] == "PasswordDeletedEvent"
    assert delete_event["priority"] == "HIGH"

    # Step 8: Verify events are chronologically ordered
    new_events = after_delete_events[initial_count:]
    for i in range(len(new_events) - 1):
        current_time = new_events[i]["occurred_on"]
        next_time = new_events[i + 1]["occurred_on"]
        assert current_time <= next_time, "Events should be ordered chronologically"


def test_event_logs_requires_admin_permission(
    e2e_client, configured_sso, sso_user_factory, setup
):
    """
    Verify that non-admin users cannot access event logs.
    """
    # Create a regular SSO user (not admin)
    regular_user = sso_user_factory("regularuser@example.com", "Regular User")
    user_client = regular_user["client"]

    # Try to access event logs as regular user
    response = user_client.get("/api/events")
    assert response.status_code == 403
    assert "administrators" in response.json()["detail"].lower()


def test_event_logs_requires_authentication(e2e_client):
    """
    Verify that unauthenticated users cannot access event logs.
    """
    response = e2e_client.get("/api/events")
    assert response.status_code == 401


def test_event_logs_filter_by_user_id(
    authenticated_admin_client, setup, admin_personal_group_id, admin_user_id
):
    """
    Test filtering event logs by user_id to see events related to a specific user.
    """
    # Step 1: Create a password as admin user
    create_response = authenticated_admin_client.post(
        "/api/passwords",
        json={
            "name": "User-specific Password",
            "password": "SecureP@ss123",
            "folder": "User Test",
            "group_id": admin_personal_group_id,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]

    # Step 2: Filter events by admin_user_id
    filter_response = authenticated_admin_client.get(
        f"/api/events?user_id={admin_user_id}"
    )
    assert filter_response.status_code == 200
    filtered_events = filter_response.json()["events"]

    # Step 3: Verify the filtered events contain the recent password creation
    # The filtered list should include at least the password creation event
    assert len(filtered_events) > 0

    # Find the most recent event (should be PasswordCreatedEvent)
    latest_event = filtered_events[-1]
    assert latest_event["event_type"] == "PasswordCreatedEvent"

    # Step 4: Clean up - delete the password
    delete_response = authenticated_admin_client.delete(f"/api/passwords/{password_id}")
    assert delete_response.status_code == 204

    # Step 5: Verify filtering still works after deletion
    filter_response_after = authenticated_admin_client.get(
        f"/api/events?user_id={admin_user_id}"
    )
    assert filter_response_after.status_code == 200
    filtered_events_after = filter_response_after.json()["events"]

    # Should now include both create and delete events
    assert len(filtered_events_after) > len(filtered_events)
