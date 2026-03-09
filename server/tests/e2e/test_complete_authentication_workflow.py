"""
Complete End-to-End Authentication Workflow.

This test covers the entire authentication system in one comprehensive workflow:
1. Cookie-based authentication (register, login, verify cookies)
2. Protected endpoint access (authenticated vs unauthenticated)
3. User information endpoint (/users/me)
4. CSRF protection lifecycle
5. SSO authentication flow (configuration, URL, callback)
6. Refresh token workflow
7. Token validation with protected endpoints
"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest


@pytest.mark.asyncio
async def test_complete_authentication_workflow(
    e2e_client, oidc_server, oidc_test_user, client_factory, session_vault_setup_data
):
    """
    Complete authentication workflow covering all authentication features.

    This single test validates the entire authentication system step by step:
    - Cookie-based authentication
    - User information retrieval
    - CSRF protection
    - SSO authentication
    - Token refresh mechanism

    Note: Uses session_vault_setup_data to set up vault, then creates admin fresh.
    """

    print("\n" + "=" * 80)
    print("🚀 STARTING COMPLETE AUTHENTICATION WORKFLOW TEST")
    print("=" * 80)

    # =========================================================================
    # PHASE 1: COOKIE-BASED AUTHENTICATION
    # =========================================================================
    print("\n" + "=" * 80)
    print("📝 PHASE 1: COOKIE-BASED AUTHENTICATION")
    print("=" * 80)

    # Step 1.1: Register admin user
    print("\n📝 Step 1.1: Registering admin user...")
    admin_data = {
        "email": "admin@example.com",
        "password": "securepassword123",
        "display_name": "Test Admin",
    }
    register_response = e2e_client.post("/api/auth/register-admin", json=admin_data)
    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["email"] == admin_data["email"]
    assert register_data["display_name"] == admin_data["display_name"]
    assert register_data["message"] == "Admin registered successfully"
    print("✅ Admin user registered successfully")

    # Step 1.2: Login and verify cookies are set
    print("\n🔐 Step 1.2: Logging in and verifying cookies...")
    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "securepassword123",
        },
    )
    assert login_response.status_code == 200

    # Verify cookies are set
    cookies = login_response.cookies
    assert "access_token" in cookies, "access_token cookie should be set"
    assert "refresh_token" in cookies, "refresh_token cookie should be set"

    access_token = cookies.get("access_token")
    refresh_token = cookies.get("refresh_token")
    assert access_token is not None
    assert len(access_token) > 0
    assert refresh_token is not None
    assert len(refresh_token) > 0
    print("✅ Login successful - cookies set (access_token, refresh_token)")

    # =========================================================================
    # PHASE 2: USER INFORMATION ENDPOINT
    # =========================================================================
    print("\n" + "=" * 80)
    print("👤 PHASE 2: USER INFORMATION ENDPOINT")
    print("=" * 80)

    # Step 2.1: Get current user information (authenticated)
    print("\n👤 Step 2.1: Getting current user information...")
    me_response = e2e_client.get("/api/users/me")
    assert me_response.status_code == 200

    user_data = me_response.json()
    assert "id" in user_data
    assert "username" in user_data
    assert "email" in user_data
    assert "name" in user_data
    assert "roles" in user_data
    assert "is_sso" in user_data
    assert "personal_group_id" in user_data

    assert user_data["email"] == "admin@example.com"
    assert user_data["name"] == "Test Admin"
    assert user_data["is_sso"] is False
    assert "admin" in user_data["roles"]

    admin_personal_group_id = user_data["personal_group_id"]
    print(f"✅ User info retrieved: {user_data['email']} (ID: {user_data['id']})")
    print(f"   Personal Group ID: {admin_personal_group_id}")

    # Step 2.3: Set up vault (required for password encryption)
    print("\n🔐 Step 2.3: Setting up vault with shares...")
    vault_status = e2e_client.get("/api/vault/status")
    if vault_status.json().get("needs_validation", True) or not vault_status.json().get("is_setup", False):
        # Initialize vault
        init_response = e2e_client.post(
            "/api/vault/setup",
            json={
                "nb_shares": session_vault_setup_data["nb_shares"],
                "threshold": session_vault_setup_data["threshold"],
            },
        )
        assert init_response.status_code == 201
        setup_id = init_response.json()["setup_id"]

        # Validate setup
        validate_response = e2e_client.post(
            "/api/vault/validate-setup",
            json={"setup_id": setup_id},
        )
        assert validate_response.status_code == 200
        print(
            f"✅ Vault initialized and validated with {session_vault_setup_data['threshold']}/{session_vault_setup_data['nb_shares']} shares"
        )
    else:
        print("✅ Vault already set up")

    # Step 2.2: Verify unauthenticated request fails
    print("\n🚫 Step 2.2: Verifying unauthenticated request fails...")
    unauthenticated_client = client_factory()
    unauth_me_response = unauthenticated_client.get("/api/users/me")
    assert unauth_me_response.status_code == 401
    print("✅ Unauthenticated request correctly rejected (401)")

    # =========================================================================
    # PHASE 3: PROTECTED ENDPOINT ACCESS
    # =========================================================================
    print("\n" + "=" * 80)
    print("🔒 PHASE 3: PROTECTED ENDPOINT ACCESS")
    print("=" * 80)

    # Step 3.1: Create password with authenticated client (should succeed)
    print("\n✅ Step 3.1: Creating password with authenticated client...")
    password_data = {
        "name": "Test Password Entry",
        "password": "MyS3cur3P@ss!",
        "folder": "Test Folder",
        "group_id": admin_personal_group_id,
    }
    create_response = e2e_client.post("/api/passwords/", json=password_data)
    assert create_response.status_code == 201
    password_id = create_response.json()["id"]
    print(f"✅ Password created successfully (ID: {password_id})")

    # Step 3.2: Try to create password without authentication (should fail)
    print("\n🚫 Step 3.2: Attempting to create password without authentication...")
    unauth_create_response = unauthenticated_client.post("/api/passwords/", json=password_data)
    assert unauth_create_response.status_code == 401
    print("✅ Unauthenticated password creation correctly rejected (401)")

    # =========================================================================
    # PHASE 4: CSRF PROTECTION
    # =========================================================================
    print("\n" + "=" * 80)
    print("🛡️  PHASE 4: CSRF PROTECTION")
    print("=" * 80)

    # Step 4.1: Verify unauthenticated user cannot get CSRF token
    print("\n🚫 Step 4.1: Verifying unauthenticated user cannot get CSRF token...")
    unauth_csrf_response = unauthenticated_client.get("/api/auth/csrf-token")
    assert unauth_csrf_response.status_code == 401
    print("✅ CSRF token request without auth correctly rejected (401)")

    # Step 4.2: Get CSRF token as authenticated user
    print("\n🎫 Step 4.2: Getting CSRF token as authenticated user...")
    token_response = e2e_client.get("/api/auth/csrf-token")
    assert token_response.status_code == 200
    csrf_token = token_response.json()["csrf_token"]
    assert len(csrf_token) > 0
    print(f"✅ CSRF token obtained: {csrf_token[:20]}...")

    # Step 4.3: Verify GET requests work without CSRF token
    print("\n📖 Step 4.3: Verifying GET requests work without CSRF token...")
    get_groups_response = e2e_client.get("/api/groups")
    assert get_groups_response.status_code == 200
    print("✅ GET request successful without CSRF token")

    # Step 4.4: Test POST/PUT/DELETE without CSRF token (should be rejected)
    print("\n🚫 Step 4.4: Testing POST/PUT/DELETE without CSRF token...")
    e2e_client.disable_auto_csrf()
    no_csrf_response = e2e_client.post(
        "/api/groups/",
        json={"name": "No CSRF", "description": "Should fail"},
    )
    assert no_csrf_response.status_code == 403
    assert "CSRF token missing" in no_csrf_response.json()["detail"]
    print("✅ POST without CSRF token correctly rejected (403)")

    # PUT without CSRF token is rejected
    me = e2e_client.get("/api/users/me").json()
    put_no_csrf_response = e2e_client.put(
        f"/api/groups/{me['personal_group_id']}",
        json={"name": "No CSRF", "description": "Should fail"},
    )
    assert put_no_csrf_response.status_code == 403
    assert "CSRF token missing" in put_no_csrf_response.json()["detail"]
    print("✅ PUT without CSRF token correctly rejected (403)")

    # Step 4.5: Test POST with invalid CSRF token (should be rejected)
    print("\n🚫 Step 4.5: Testing POST with invalid CSRF token...")
    invalid_csrf_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Bad CSRF", "description": "Should fail"},
        headers={"X-CSRF-Token": "invalid_token_12345"},
    )
    assert invalid_csrf_response.status_code == 403
    assert "Invalid or expired CSRF token" in invalid_csrf_response.json()["detail"]
    print("✅ POST with invalid CSRF token correctly rejected (403)")

    # Step 4.6: Test POST with valid CSRF token (should succeed)
    print("\n✅ Step 4.6: Testing POST with valid CSRF token...")
    e2e_client.enable_auto_csrf()  # Re-enable before valid test
    valid_csrf_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Valid CSRF Group", "description": "Should succeed"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert valid_csrf_response.status_code == 201
    test_group_id = valid_csrf_response.json()["id"]
    print(f"✅ POST with valid CSRF token successful (Group ID: {test_group_id})")

    # DELETE without CSRF token is rejected
    e2e_client.disable_auto_csrf()
    delete_no_csrf_response = e2e_client.delete(f"/api/groups/{test_group_id}")
    assert delete_no_csrf_response.status_code == 403
    assert "CSRF token missing" in delete_no_csrf_response.json()["detail"]
    e2e_client.enable_auto_csrf()
    print("✅ DELETE without CSRF token correctly rejected (403)")

    # Step 4.7: Test CSRF token reuse
    print("\n🔄 Step 4.7: Testing CSRF token reuse...")
    for i in range(3):
        reuse_response = e2e_client.post(
            "/api/groups/",
            json={"name": f"Reuse Token {i}", "description": "Multi-use"},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert reuse_response.status_code == 201
    print("✅ CSRF token successfully reused across 3 requests")

    # Step 4.8: Test CSRF token regeneration invalidates old token
    print("\n🔄 Step 4.8: Testing CSRF token regeneration...")
    new_token_response = e2e_client.get("/api/auth/csrf-token")
    new_csrf_token = new_token_response.json()["csrf_token"]
    assert new_csrf_token != csrf_token
    print(f"✅ New CSRF token generated: {new_csrf_token[:20]}...")

    # Old token should be rejected
    old_token_response = e2e_client.post(
        "/api/groups/",
        json={"name": "Old Token", "description": "Should fail"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert old_token_response.status_code == 403
    print("✅ Old CSRF token correctly rejected after regeneration")

    # New token should work
    new_token_test_response = e2e_client.post(
        "/api/groups/",
        json={"name": "New Token", "description": "Should succeed"},
        headers={"X-CSRF-Token": new_csrf_token},
    )
    assert new_token_test_response.status_code == 201
    print("✅ New CSRF token works correctly")

    # Step 4.9: Verify refresh token endpoint is exempt from CSRF
    print("\n🔄 Step 4.9: Verifying refresh token endpoint is exempt from CSRF...")
    refresh_csrf_response = e2e_client.post("/api/auth/refresh-token")
    assert refresh_csrf_response.status_code != 403 or "CSRF" not in refresh_csrf_response.json().get("detail", "")
    print("✅ Refresh token endpoint correctly exempt from CSRF protection")

    # =========================================================================
    # PHASE 5: SSO AUTHENTICATION
    # =========================================================================
    print("\n" + "=" * 80)
    print("🔗 PHASE 5: SSO AUTHENTICATION")
    print("=" * 80)

    # Step 5.1: Check SSO status before configuration
    print("\n📊 Step 5.1: Checking SSO status before configuration...")
    status_before_response = e2e_client.get("/api/auth/sso/is-configured")
    assert status_before_response.status_code == 200
    assert status_before_response.json()["is_set"] is False
    print("✅ SSO status: Not configured")

    # Step 5.2: Configure SSO provider
    print("\n📝 Step 5.2: Configuring SSO provider...")
    configure_response = e2e_client.post(
        "/api/auth/sso/configure",
        json={
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
            "discovery_url": oidc_server["discovery_url"],
        },
    )
    assert configure_response.status_code == 200
    print("✅ SSO provider configured successfully")

    # Step 5.3: Verify SSO status after configuration
    print("\n📊 Step 5.3: Checking SSO status after configuration...")
    status_after_response = e2e_client.get("/api/auth/sso/is-configured")
    assert status_after_response.status_code == 200
    assert status_after_response.json()["is_set"] is True
    print("✅ SSO status: Configured")

    # Step 5.4: Get SSO authorization URL
    print("\n🔗 Step 5.4: Getting SSO authorization URL...")
    url_response = e2e_client.get("/api/auth/sso/url")
    assert url_response.status_code == 200

    sso_url_data = url_response.json()
    if isinstance(sso_url_data, str):
        sso_url = sso_url_data
    elif isinstance(sso_url_data, dict) and "url" in sso_url_data:
        sso_url = sso_url_data["url"]
    else:
        sso_url = str(sso_url_data)

    assert isinstance(sso_url, str)
    assert "http" in sso_url.lower()
    print(f"✅ SSO authorization URL obtained: {sso_url[:50]}...")

    # Step 5.5: Test invalid authorization code
    print("\n🚫 Step 5.5: Testing SSO callback with invalid code...")
    invalid_callback_response = e2e_client.get("/api/auth/sso/callback?code=invalid-code-12345")
    assert invalid_callback_response.status_code == 400
    error_data = invalid_callback_response.json()
    assert (
        "SSO authentication failed" in error_data["detail"]
        or "invalid" in error_data["detail"].lower()
        or "fail" in error_data["detail"].lower()
    )
    print("✅ Invalid SSO code correctly rejected (400)")

    # Step 5.6: Simulate user authorization and get valid code
    print("\n🔐 Step 5.6: Simulating user authorization to get valid code...")
    auth_response = httpx.post(
        sso_url,
        data={"sub": oidc_test_user["sub"]},
        follow_redirects=False,
    )
    assert auth_response.status_code in [302, 303]

    callback_url = auth_response.headers.get("location")
    assert callback_url

    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    valid_code = query_params.get("code", [None])[0]
    assert valid_code
    print(f"✅ Valid authorization code obtained: {valid_code[:10]}...")

    # Step 5.7: Complete SSO login with valid code
    print("\n✨ Step 5.7: Completing SSO login with valid code...")
    valid_callback_response = e2e_client.get(f"/api/auth/sso/callback?code={valid_code}")
    assert valid_callback_response.status_code == 200

    callback_data = valid_callback_response.json()
    assert "message" in callback_data
    assert "user" in callback_data

    # Extract SSO tokens from cookies
    sso_access_token = valid_callback_response.cookies.get("access_token")
    sso_refresh_token = valid_callback_response.cookies.get("refresh_token")
    assert sso_access_token is not None
    assert sso_refresh_token is not None

    sso_user_info = callback_data["user"]
    assert sso_user_info["email"] == oidc_test_user["email"]
    assert sso_user_info["display_name"] == oidc_test_user["name"]
    sso_user_id = sso_user_info["user_id"]
    print(f"✅ SSO login successful for {sso_user_info['email']}")
    print("✅ SSO tokens set in cookies")

    # Refresh CSRF token after SSO authentication
    if hasattr(e2e_client, "refresh_csrf_token"):
        e2e_client.refresh_csrf_token()

    # Step 5.8: Validate SSO token by getting user info
    print("\n👤 Step 5.8: Validating SSO token with /users/me...")
    sso_me_response = e2e_client.get("/api/users/me")
    assert sso_me_response.status_code == 200

    sso_user_data = sso_me_response.json()
    assert sso_user_data["email"] == oidc_test_user["email"]
    assert sso_user_data["name"] == oidc_test_user["name"]
    assert sso_user_data["id"] == sso_user_id
    assert sso_user_data["is_sso"] is True

    sso_personal_group_id = sso_user_data["personal_group_id"]
    print(f"✅ SSO user info validated: {sso_user_data['email']}")
    print(f"   SSO User Personal Group ID: {sso_personal_group_id}")

    # Step 5.9: Validate SSO token by creating a password
    print("\n🔑 Step 5.9: Validating SSO token by creating a password...")
    sso_password_response = e2e_client.post(
        "/api/passwords/",
        json={
            "name": "SSO Test Password",
            "password": "SuperSecure123!@#",
            "folder": "SSO Tests",
            "group_id": sso_personal_group_id,
        },
    )
    assert sso_password_response.status_code == 201
    sso_password_id = sso_password_response.json()["id"]
    assert sso_password_id is not None
    print(f"✅ SSO token validated with password creation (ID: {sso_password_id})")

    # =========================================================================
    # PHASE 6: REFRESH TOKEN WORKFLOW
    # =========================================================================
    print("\n" + "=" * 80)
    print("🔄 PHASE 6: REFRESH TOKEN WORKFLOW")
    print("=" * 80)

    # Step 6.1: Use refresh token to get new access token
    print("\n🔄 Step 6.1: Using refresh token to get new access token...")
    # Set refresh token cookie explicitly
    e2e_client.cookies.set("refresh_token", sso_refresh_token)

    refresh_response = e2e_client.post("/api/auth/refresh-token")
    assert refresh_response.status_code == 200

    refresh_data = refresh_response.json()
    assert "message" in refresh_data
    assert refresh_data["message"] == "Access token refreshed successfully"

    # Extract new access token from cookie
    new_access_token = refresh_response.cookies.get("access_token")
    assert new_access_token is not None
    assert new_access_token != sso_access_token
    print("✅ New access token obtained successfully")
    print(f"   Old token: {sso_access_token[:20]}...")
    print(f"   New token: {new_access_token[:20]}...")

    # Step 6.2: Validate new access token works
    print("\n✅ Step 6.2: Validating new access token...")
    # The new token is already set in cookies by the refresh response
    validate_response = e2e_client.get("/api/users/me")
    assert validate_response.status_code == 200

    validated_user = validate_response.json()
    assert validated_user["email"] == oidc_test_user["email"]
    print(f"✅ New access token validated successfully for {validated_user['email']}")

    # =========================================================================
    # FINAL VALIDATION
    # =========================================================================
    print("\n" + "=" * 80)
    print("🎉 ALL PHASES COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\n✅ Phase 1: Cookie-based authentication")
    print("✅ Phase 2: User information endpoint")
    print("✅ Phase 3: Protected endpoint access")
    print("✅ Phase 4: CSRF protection")
    print("✅ Phase 5: SSO authentication")
    print("✅ Phase 6: Refresh token workflow")
    print("\n" + "=" * 80)
    print("🎊 COMPLETE AUTHENTICATION WORKFLOW TEST PASSED!")
    print("=" * 80 + "\n")
