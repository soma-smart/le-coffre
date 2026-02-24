import httpx
from urllib.parse import quote, urlparse, parse_qs


def create_sso_user_in_provider(oidc_server, email, name):
    """Helper to create a user in the OIDC provider mock."""
    user_data = {
        "sub": email,
        "email": email,
        "name": name,
        "given_name": name.split()[0] if " " in name else name,
        "family_name": name.split()[-1] if " " in name else "",
    }

    response = httpx.put(
        f"{oidc_server['issuer_url']}/users/{quote(user_data['sub'])}",
        json=user_data,
    )
    assert response.status_code == 204

    return {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data["name"],
        "oidc_server": oidc_server,
    }


def authenticate_sso_user(e2e_client, oidc_server, sso_user):
    """Helper to authenticate an SSO user and get their token."""
    url_response = e2e_client.get("/api/auth/sso/url")
    assert url_response.status_code == 200

    sso_url_data = url_response.json()
    if isinstance(sso_url_data, str):
        sso_url = sso_url_data
    elif isinstance(sso_url_data, dict) and "url" in sso_url_data:
        sso_url = sso_url_data["url"]
    else:
        sso_url = str(sso_url_data)

    auth_response = httpx.post(
        sso_url,
        data={"sub": sso_user["sub"]},
        follow_redirects=False,
    )
    assert auth_response.status_code in [302, 303]

    callback_url = auth_response.headers.get("location")
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    valid_code = query_params.get("code", [None])[0]
    assert valid_code

    valid_callback_response = e2e_client.get(
        f"/api/auth/sso/callback?code={valid_code}"
    )
    assert valid_callback_response.status_code == 200

    callback_data = valid_callback_response.json()
    token = valid_callback_response.cookies.get("access_token")
    assert token is not None

    return {
        "token": token,
        "user_id": callback_data["user"]["user_id"],
        "email": callback_data["user"]["email"],
        "display_name": callback_data["user"]["display_name"],
    }


def test_complete_admin_authentication_flow(
    e2e_client, unauthenticated_client, oidc_server, client_factory
):
    """
    End-to-end test that:
    1. Registers an admin
    2. Logs in with the admin credentials
    3. Sets up the vault
    4. Configures SSO
    5. Creates a random SSO user
    6. Tries to delete the user without cookie (should fail)
    7. Tries to delete the user with invalid cookie (should fail)
    8. Deletes the user with valid admin cookie (should succeed)
    """
    admin_data = {
        "email": "admin@example.com",
        "password": "secure_password123",
        "display_name": "Test Administrator",
    }

    # Step 1: Register admin
    register_response = e2e_client.post("/api/auth/register-admin", json=admin_data)

    assert register_response.status_code == 201
    register_data = register_response.json()

    assert register_data["email"] == admin_data["email"]
    assert register_data["display_name"] == admin_data["display_name"]
    assert register_data["message"] == "Admin registered successfully"

    # Step 2: Try login with wrong password
    login_data = {"email": admin_data["email"], "password": "wrong_password"}

    login_response = e2e_client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 401

    # Step 3: Login with correct password
    login_data = {"email": admin_data["email"], "password": admin_data["password"]}

    login_response = e2e_client.post("/api/auth/login", json=login_data)

    assert login_response.status_code == 200
    login_result = login_response.json()

    assert login_result["email"] == admin_data["email"]
    assert login_result["message"] == "Login successful"

    # Extract JWT token from cookie
    jwt_token = login_response.cookies.get("access_token")
    assert jwt_token is not None

    # Refresh CSRF token after login (for CsrfTestClient)
    if hasattr(e2e_client, "refresh_csrf_token"):
        e2e_client.refresh_csrf_token()

    # Step 4: Setup the vault (required for SSO configuration)
    setup_response = e2e_client.post(
        "/api/vault/setup",
        json={"nb_shares": 5, "threshold": 3},
    )
    assert setup_response.status_code == 201
    setup_data = setup_response.json()
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    validate_response = e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )
    assert validate_response.status_code == 200

    # Step 5: Configure SSO
    sso_config_response = e2e_client.post(
        "/api/auth/sso/configure",
        json={
            "discovery_url": oidc_server["discovery_url"],
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
        },
    )
    assert sso_config_response.status_code == 200, (
        f"SSO config failed: {sso_config_response.text}"
    )

    # Step 6: Create a random SSO user to delete later
    # Use a separate client to avoid overwriting admin's cookie
    sso_user_client = client_factory()
    sso_user = create_sso_user_in_provider(
        oidc_server, "testuser_1234@example.com", "Test User"
    )
    user_data = authenticate_sso_user(sso_user_client, oidc_server, sso_user)
    user_id = user_data["user_id"]

    # Step 7: Check that the user exists
    assert e2e_client.get(f"/api/users/{user_id}").status_code == 200

    # Step 8: Try to delete user without authorization (no cookie) - should fail
    # Disable auto CSRF to test auth independently
    unauthenticated_client.disable_auto_csrf()
    delete_response_no_auth = unauthenticated_client.delete(f"/api/users/{user_id}")
    assert delete_response_no_auth.status_code == 401

    # Step 9: Try to delete user with invalid cookie (should fail)
    unauthenticated_client.cookies.set("access_token", "invalid_token")
    delete_response_invalid = unauthenticated_client.delete(f"/api/users/{user_id}")
    # With invalid JWT, middleware returns to auth check which returns 401
    # But with CSRF middleware, if access_token cookie exists, CSRF is checked first
    # Since we disabled auto_csrf, no CSRF token is sent, so we get 403
    # This is actually the correct behavior: CSRF is checked before JWT validation
    assert delete_response_invalid.status_code == 403
    unauthenticated_client.enable_auto_csrf()

    # Step 10: Delete user with valid admin cookie (should succeed)
    # e2e_client already has the valid cookie from login
    delete_response_valid = e2e_client.delete(f"/api/users/{user_id}")
    assert delete_response_valid.status_code == 204

    # Step 11: Verify user is actually deleted by trying to get it
    get_response = e2e_client.get(f"/api/users/{user_id}")
    assert get_response.status_code == 404
