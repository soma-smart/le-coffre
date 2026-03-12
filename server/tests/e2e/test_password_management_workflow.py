"""
Complete end-to-end test for password management workflow.

This consolidated test covers the entire password lifecycle including:
- CRUD operations (Create, Read, Update, Delete)
- List passwords by folder
- Sharing and unsharing with other users
- Group-based sharing
- Access control verification
- Event logging
- Access listing
- Timestamp tracking (created_at, last_updated_at)
"""

import time
from uuid import UUID

import jwt

STRONG_PASSWORD = "StrongP@ssw0rd123"
LOGIN = "My Login"
URL = "http://example.com"


def get_user_id_from_token(token: str) -> str:
    """Extract user_id from JWT token"""
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded["user_id"]


def test_complete_password_management_workflow(client_factory, setup, configured_sso, sso_user_token):
    """
    Complete workflow covering all password management operations:

    Phase 1: Basic CRUD Operations
    - Create password and verify timestamps
    - Read password
    - Update password and verify timestamp changes
    - List passwords by folder
    - Delete password and verify removal

    Phase 2: Sharing and Access Control
    - Create password for sharing tests
    - Verify user cannot access before sharing
    - Share password with another user
    - Verify shared access
    - List access permissions
    - Unshare password
    - Verify access revoked

    Phase 3: Group-Based Sharing
    - Create a group
    - Add user to group as member
    - Share password with group
    - Verify group member access

    Phase 4: Event Logging
    - Verify all operations generate events
    - Check event ordering and types

    Phase 5: Authorization Tests
    - Verify authentication is required
    - Verify non-existent resource handling
    """
    # Create separate clients for admin and SSO user
    admin_client = client_factory()
    sso_client = client_factory()
    unauthenticated_client = client_factory()

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

    # Get admin's personal group ID and user ID
    admin_response = admin_client.get("/api/users/me")
    assert admin_response.status_code == 200
    admin_group_id = admin_response.json()["personal_group_id"]
    admin_user_id = admin_response.json()["id"]

    # Get SSO user's personal group ID and user ID
    sso_user_response = sso_client.get("/api/users/me")
    assert sso_user_response.status_code == 200
    sso_user_group_id = sso_user_response.json()["personal_group_id"]
    sso_user_id = sso_user_response.json()["id"]

    # ===================================================================
    # PHASE 1: BASIC CRUD OPERATIONS
    # ===================================================================

    print("\n=== PHASE 1: BASIC CRUD OPERATIONS ===")

    # Step 1.1: CREATE - Create a password and verify timestamps
    print("Step 1.1: Creating password...")
    create_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Work",
            "group_id": admin_group_id,
            "login": LOGIN,
            "url": URL,
        },
    )
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]
    print(f"✓ Password created with ID: {password_id}")

    # Step 1.2: READ - Verify password was created with timestamps
    print("Step 1.2: Reading password and checking timestamps...")
    get_response = admin_client.get(f"/api/passwords/{password_id}")
    assert get_response.status_code == 200
    assert get_response.json()["password"] == STRONG_PASSWORD

    list_meta_response = admin_client.get("/api/passwords/list")
    assert list_meta_response.status_code == 200
    password_meta = next(p for p in list_meta_response.json() if p["id"] == password_id)
    assert password_meta["name"] == "Test Password"
    assert password_meta["folder"] == "Work"
    assert password_meta["login"] == LOGIN
    assert password_meta["url"] == URL

    # Verify timestamps exist and are valid
    assert "created_at" in password_meta
    assert password_meta["created_at"] is not None
    assert "last_updated_at" in password_meta
    assert password_meta["last_updated_at"] is not None

    original_created_at = password_meta["created_at"]
    original_updated_at = password_meta["last_updated_at"]
    print(f"✓ Password retrieved with created_at: {original_created_at}")
    print(f"✓ Password retrieved with last_updated_at: {original_updated_at}")

    # Small delay to ensure timestamp will be different after update
    time.sleep(0.1)

    # Step 1.3: UPDATE - Update the password and verify timestamp changes
    print("Step 1.3: Updating password...")
    update_response = admin_client.put(
        f"/api/passwords/{password_id}",
        json={
            "name": "Updated Password",
            "password": "NewStrongP@ssw0rd!",
            "folder": "Personal",
            "login": "NEW " + LOGIN,
            "url": "NEW " + URL,
        },
    )
    assert update_response.status_code == 201
    print("✓ Password updated successfully")

    # Step 1.4: READ AFTER UPDATE - Verify update and timestamp changes
    print("Step 1.4: Verifying update and timestamp changes...")
    get_updated = admin_client.get(f"/api/passwords/{password_id}")
    assert get_updated.status_code == 200
    assert get_updated.json()["password"] == "NewStrongP@ssw0rd!"

    list_updated_response = admin_client.get("/api/passwords/list")
    assert list_updated_response.status_code == 200
    updated_meta = next(p for p in list_updated_response.json() if p["id"] == password_id)
    assert updated_meta["name"] == "Updated Password"
    assert updated_meta["folder"] == "Personal"
    assert updated_meta["login"] == "NEW " + LOGIN
    assert updated_meta["url"] == "NEW " + URL

    # Verify timestamps: created_at should stay same, last_updated_at should change
    assert updated_meta["created_at"] == original_created_at, "created_at should not change after update"
    assert updated_meta["last_updated_at"] != original_updated_at, "last_updated_at should change after update"
    assert updated_meta["last_updated_at"] > original_updated_at, "last_updated_at should be more recent"

    print(f"✓ created_at unchanged: {updated_meta['created_at']}")
    print(f"✓ last_updated_at changed: {updated_meta['last_updated_at']}")

    # Step 1.5: CREATE MORE PASSWORDS - Create additional passwords for list testing
    print("Step 1.5: Creating additional passwords for folder listing...")
    for i in range(2, 4):
        response = admin_client.post(
            "/api/passwords",
            json={
                "name": f"Test Password {i}",
                "password": f"StrongP@ssw0rd{i}!",
                "folder": "Work",
                "login": f"user{i}",
                "url": f"http://example_{i}.com",
                "group_id": admin_group_id,
            },
        )
        assert response.status_code == 201
    print("✓ Additional passwords created")

    # Step 1.6: LIST PASSWORDS - Verify list includes all passwords with timestamps
    print("Step 1.6: Listing passwords by folder...")
    list_response = admin_client.get("/api/passwords/list?folder=Work")
    assert list_response.status_code == 200
    passwords = list_response.json()
    assert len(passwords) >= 2, "Should have at least 2 passwords in Work folder"

    # Verify each password has timestamps
    for password in passwords:
        assert "created_at" in password, "Each password should have created_at"
        assert password["created_at"] is not None
        assert "last_updated_at" in password, "Each password should have last_updated_at"
        assert password["last_updated_at"] is not None

    print(f"✓ Found {len(passwords)} passwords in 'Work' folder with timestamps")

    # Step 1.7: LIST NON-EXISTENT FOLDER - Verify 404 for non-existent folder
    print("Step 1.7: Testing non-existent folder...")
    list_404_response = admin_client.get("/api/passwords/list?folder=NonExistent")
    assert list_404_response.status_code == 404
    print("✓ Non-existent folder returns 404 as expected")

    # Step 1.8: DELETE - Delete the updated password
    print("Step 1.8: Deleting password...")
    delete_response = admin_client.delete(f"/api/passwords/{password_id}")
    assert delete_response.status_code == 204
    print("✓ Password deleted successfully")

    # Step 1.9: VERIFY DELETED - Confirm password no longer exists
    print("Step 1.9: Verifying password was deleted...")
    get_deleted = admin_client.get(f"/api/passwords/{password_id}")
    assert get_deleted.status_code == 404
    print("✓ Password confirmed deleted (404)")

    # Step 1.10: SSO USER CREATES THEIR OWN PASSWORD
    print("Step 1.10: SSO user creates their own password...")
    sso_create_response = sso_client.post(
        "/api/passwords",
        json={
            "name": "SSO User Password",
            "password": STRONG_PASSWORD,
            "folder": "Work",
            "group_id": sso_user_group_id,
        },
    )
    assert sso_create_response.status_code == 201
    sso_password_id = sso_create_response.json()["id"]
    print(f"✓ SSO user password created: {sso_password_id}")

    # Step 1.11: ADMIN LISTS ALL PASSWORDS
    # Admin should see every password regardless of ownership.
    # Passwords the admin owns → can_read=True, can_write=True.
    # Passwords the admin has no group access to → can_read=False, can_write=False.
    print("Step 1.11: Admin lists all passwords (should see all, with access flags reflecting group membership)...")
    admin_list_response = admin_client.get("/api/passwords/list")
    assert admin_list_response.status_code == 200
    admin_passwords = admin_list_response.json()

    all_ids = [p["id"] for p in admin_passwords]
    assert sso_password_id in all_ids, "Admin should see SSO user's password"

    sso_password_entry = next(p for p in admin_passwords if p["id"] == sso_password_id)
    assert sso_password_entry["can_read"] is False, "Admin should have can_read=False for SSO user's password"
    assert sso_password_entry["can_write"] is False, "Admin should have can_write=False for SSO user's password"

    admin_owned = [p for p in admin_passwords if p["id"] != sso_password_id]
    for p in admin_owned:
        assert p["can_read"] is True, f"Admin password {p['id']} (owned by admin) should have can_read=True"
        assert p["can_write"] is True, f"Admin password {p['id']} (owned by admin) should have can_write=True"
    print(
        f"✓ Admin sees {len(admin_passwords)} passwords, own passwords with full access and SSO user's password with no access"
    )

    # Step 1.12: SSO USER LISTS THEIR OWN PASSWORDS
    # Regular user should only see their own passwords, with correct permission flags
    print("Step 1.12: SSO user lists their own passwords (can_read=True, can_write=True)...")
    sso_list_response = sso_client.get("/api/passwords/list")
    assert sso_list_response.status_code == 200
    sso_passwords = sso_list_response.json()

    sso_password_ids = [p["id"] for p in sso_passwords]
    assert sso_password_id in sso_password_ids, "SSO user should see their own password"
    for p in sso_passwords:
        assert p["can_read"] is True, f"SSO user password {p['id']} should have can_read=True"
        assert p["can_write"] is True, f"SSO user password {p['id']} should have can_write=True"
    print(f"✓ SSO user sees {len(sso_passwords)} password(s), all with can_read=True and can_write=True")

    # ===================================================================
    # PHASE 2: SHARING AND ACCESS CONTROL
    # ===================================================================

    print("\n=== PHASE 2: SHARING AND ACCESS CONTROL ===")

    # Step 2.1: CREATE - Create a new password for sharing tests
    print("Step 2.1: Creating password for sharing tests...")
    create_share_response = admin_client.post(
        "/api/passwords",
        json={
            "name": "Shared Test Password",
            "password": STRONG_PASSWORD,
            "folder": "Shared",
            "group_id": admin_group_id,
            "login": LOGIN,
            "url": URL,
        },
    )
    assert create_share_response.status_code == 201
    shared_password_id = create_share_response.json()["id"]
    print(f"✓ Password created for sharing: {shared_password_id}")

    # Step 2.2: VERIFY OWNER ACCESS
    print("Step 2.2: Verifying owner can access password...")
    get_owner_response = admin_client.get(f"/api/passwords/{shared_password_id}")
    assert get_owner_response.status_code == 200
    assert get_owner_response.json()["password"] == STRONG_PASSWORD
    print("✓ Owner has access")

    # Step 2.3: VERIFY NO ACCESS BEFORE SHARING
    print("Step 2.3: Verifying SSO user cannot access before sharing...")
    get_before_share = sso_client.get(f"/api/passwords/{shared_password_id}")
    assert get_before_share.status_code == 404
    print("✓ SSO user correctly denied access (404)")

    # Step 2.4: LIST ACCESS - Should show only owner
    print("Step 2.4: Listing access (should show only owner)...")
    list_access_response = admin_client.get(f"/api/passwords/{shared_password_id}/access")
    assert list_access_response.status_code == 200
    access_data = list_access_response.json()
    assert access_data["resource_id"] == shared_password_id
    assert len(access_data["user_access_list"]) == 1
    assert len(access_data["group_access_list"]) == 1

    user_access = access_data["user_access_list"][0]
    assert user_access["user_id"] == admin_user_id
    assert user_access["is_owner"] is True
    print("✓ Only owner in access list")

    # Step 2.5: NON-OWNER CANNOT LIST ACCESS
    print("Step 2.5: Verifying non-owner cannot list access...")
    list_access_non_owner = sso_client.get(f"/api/passwords/{shared_password_id}/access")
    assert list_access_non_owner.status_code == 403
    print("✓ Non-owner correctly denied permission to list access (403)")

    # Step 2.6: SHARE PASSWORD
    print("Step 2.6: Sharing password with SSO user...")
    share_response = admin_client.post(
        f"/api/passwords/{shared_password_id}/share",
        json={"group_id": sso_user_group_id},
    )
    assert share_response.status_code == 201
    assert "successfully shared" in share_response.json()["message"]
    print("✓ Password shared successfully")

    # Step 2.7: VERIFY SHARED ACCESS
    print("Step 2.7: Verifying SSO user can now access password...")
    get_after_share = sso_client.get(f"/api/passwords/{shared_password_id}")
    assert get_after_share.status_code == 200
    assert get_after_share.json()["password"] == STRONG_PASSWORD

    sso_list_meta = sso_client.get("/api/passwords/list")
    assert sso_list_meta.status_code == 200
    shared_meta = next(p for p in sso_list_meta.json() if p["id"] == shared_password_id)
    assert shared_meta["name"] == "Shared Test Password"
    assert shared_meta["login"] == LOGIN
    assert shared_meta["url"] == URL
    print("✓ SSO user can access shared password")

    # Step 2.8: LIST ACCESS AFTER SHARING - Should show owner + shared user
    print("Step 2.8: Listing access after sharing...")
    list_access_after = admin_client.get(f"/api/passwords/{shared_password_id}/access")
    assert list_access_after.status_code == 200
    access_data_shared = list_access_after.json()
    assert len(access_data_shared["user_access_list"]) == 2
    assert len(access_data_shared["group_access_list"]) == 2

    # Verify both users are in the list
    user_ids = [u["user_id"] for u in access_data_shared["user_access_list"]]
    assert admin_user_id in user_ids
    assert sso_user_id in user_ids
    print("✓ Both owner and shared user in access list")

    # Step 2.9: UNSHARE PASSWORD
    print("Step 2.9: Unsharing password from SSO user...")
    unshare_response = admin_client.delete(f"/api/passwords/{shared_password_id}/share/{sso_user_group_id}")
    assert unshare_response.status_code == 204
    print("✓ Password unshared successfully")

    # Step 2.10: VERIFY ACCESS REVOKED
    print("Step 2.10: Verifying SSO user access was revoked...")
    get_after_unshare = sso_client.get(f"/api/passwords/{shared_password_id}")
    assert get_after_unshare.status_code == 404
    print("✓ SSO user correctly denied access after unshare (404)")

    # Step 2.11: VERIFY OWNER STILL HAS ACCESS
    print("Step 2.11: Verifying owner still has access...")
    get_owner_final = admin_client.get(f"/api/passwords/{shared_password_id}")
    assert get_owner_final.status_code == 200
    print("✓ Owner still has access")

    # ===================================================================
    # PHASE 3: GROUP-BASED SHARING
    # ===================================================================

    print("\n=== PHASE 3: GROUP-BASED SHARING ===")

    # Step 3.1: CREATE GROUP
    print("Step 3.1: Creating a group...")
    group_data = {"name": "Engineering Team"}
    create_group_response = admin_client.post("/api/groups/", json=group_data)
    assert create_group_response.status_code == 201
    group = create_group_response.json()
    group_id = group["id"]
    print(f"✓ Group created: {group['name']} ({group_id})")

    # Step 3.2: ADD MEMBER TO GROUP
    print("Step 3.2: Adding SSO user to group as member...")
    add_member_data = {"user_id": sso_user_id}
    add_member_response = admin_client.post(f"/api/groups/{group_id}/members", json=add_member_data)
    assert add_member_response.status_code == 201
    print("✓ SSO user added to group")

    # Step 3.3: VERIFY NO ACCESS BEFORE GROUP SHARE
    print("Step 3.3: Verifying SSO user cannot access password...")
    get_before_group_share = sso_client.get(f"/api/passwords/{shared_password_id}")
    assert get_before_group_share.status_code == 404
    print("✓ SSO user correctly denied access (404)")

    # Step 3.4: SHARE WITH GROUP
    print("Step 3.4: Sharing password with group...")
    share_group_response = admin_client.post(
        f"/api/passwords/{shared_password_id}/share",
        json={"group_id": group_id},
    )
    assert share_group_response.status_code == 201
    print("✓ Password shared with group")

    # Step 3.5: VERIFY GROUP MEMBER ACCESS
    print("Step 3.5: Verifying group member can access password...")
    get_after_group_share = sso_client.get(f"/api/passwords/{shared_password_id}")
    assert get_after_group_share.status_code == 200
    assert get_after_group_share.json()["password"] == STRONG_PASSWORD

    group_member_list = sso_client.get("/api/passwords/list")
    assert group_member_list.status_code == 200
    group_shared_meta = next(p for p in group_member_list.json() if p["id"] == shared_password_id)
    assert group_shared_meta["name"] == "Shared Test Password"
    assert group_shared_meta["login"] == LOGIN
    assert group_shared_meta["url"] == URL
    print("✓ Group member can access shared password")

    # ===================================================================
    # PHASE 4: EVENT LOGGING
    # ===================================================================

    print("\n=== PHASE 4: EVENT LOGGING ===")

    # Step 4.1: LIST EVENTS
    print("Step 4.1: Listing password events...")
    events_response = admin_client.get(f"/api/passwords/{shared_password_id}/events")
    assert events_response.status_code == 200
    events = events_response.json()["events"]

    # Should have: created, accessed (multiple), shared (multiple), unshared
    assert len(events) >= 4, f"Expected at least 4 events, got {len(events)}"
    print(f"✓ Found {len(events)} events")

    # Step 4.2: VERIFY EVENT TYPES
    print("Step 4.2: Verifying event types...")
    event_types = [event["event_type"] for event in events]
    assert "PasswordCreatedEvent" in event_types
    assert "PasswordAccessedEvent" in event_types
    assert "PasswordSharedEvent" in event_types
    print("✓ All expected event types present")

    # Step 4.3: VERIFY EVENT ORDERING (reverse chronological)
    print("Step 4.3: Verifying event ordering...")
    for i in range(len(events) - 1):
        assert events[i]["occurred_on"] >= events[i + 1]["occurred_on"], (
            "Events should be in reverse chronological order"
        )
    print("✓ Events correctly ordered (most recent first)")

    # Step 4.4: VERIFY EVENT STRUCTURE
    print("Step 4.4: Verifying event structure...")
    for event in events:
        assert "event_id" in event
        assert "event_type" in event
        assert "occurred_on" in event
        assert "actor_user_id" in event
        assert "event_data" in event
    print("✓ All events have required fields")

    # ===================================================================
    # PHASE 5: AUTHORIZATION TESTS
    # ===================================================================

    print("\n=== PHASE 5: AUTHORIZATION TESTS ===")

    # Step 5.1: AUTHENTICATION REQUIRED - CREATE
    print("Step 5.1: Verifying authentication required for create...")
    unauth_create = unauthenticated_client.post(
        "/api/passwords",
        json={
            "name": "Unauthorized",
            "password": "test",
            "login": LOGIN,
            "url": URL,
            "group_id": admin_group_id,
        },
    )
    assert unauth_create.status_code == 401
    print("✓ Unauthenticated create correctly rejected (401)")

    # Step 5.2: AUTHENTICATION REQUIRED - READ
    print("Step 5.2: Verifying authentication required for read...")
    unauth_read = unauthenticated_client.get(f"/api/passwords/{shared_password_id}")
    assert unauth_read.status_code == 401
    print("✓ Unauthenticated read correctly rejected (401)")

    # Step 5.3: AUTHENTICATION REQUIRED - UPDATE
    print("Step 5.3: Verifying authentication required for update...")
    unauth_update = unauthenticated_client.put(
        f"/api/passwords/{shared_password_id}",
        json={
            "name": "Unauthorized",
            "password": "test",
            "folder": "test",
            "login": LOGIN,
            "url": URL,
        },
    )
    assert unauth_update.status_code == 401
    print("✓ Unauthenticated update correctly rejected (401)")

    # Step 5.4: AUTHENTICATION REQUIRED - DELETE
    print("Step 5.4: Verifying authentication required for delete...")
    unauth_delete = unauthenticated_client.delete(f"/api/passwords/{shared_password_id}")
    assert unauth_delete.status_code == 401
    print("✓ Unauthenticated delete correctly rejected (401)")

    # Step 5.5: NON-EXISTENT PASSWORD - UPDATE
    print("Step 5.5: Verifying 404 for non-existent password update...")
    nonexistent_id = str(UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7"))
    update_404 = admin_client.put(
        f"/api/passwords/{nonexistent_id}",
        json={
            "name": "Test",
            "password": "test",
            "folder": "test",
            "login": LOGIN,
            "url": URL,
        },
    )
    assert update_404.status_code == 404
    print("✓ Update non-existent password returns 404")

    # Step 5.6: NON-EXISTENT PASSWORD - DELETE
    print("Step 5.6: Verifying 404 for non-existent password delete...")
    delete_404 = admin_client.delete(f"/api/passwords/{nonexistent_id}")
    assert delete_404.status_code == 404
    print("✓ Delete non-existent password returns 404")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
