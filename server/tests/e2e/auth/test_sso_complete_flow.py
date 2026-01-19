"""End-to-end tests for SSO routes with oidc-provider-mock.

These tests validate the FastAPI routes and request/response handling for SSO authentication.
They use oidc-provider-mock which provides real OIDC endpoints for realistic E2E testing.

Note: The app in main.py uses InMemorySSOGateway by default, which simulates SSO behavior.
For full integration with real OIDC, the app would need to be configured with OAuth2SsoGateway.
"""

import pytest
import httpx
from urllib.parse import urlparse, parse_qs


@pytest.mark.asyncio
async def test_complete_sso_authentication_flow(
    e2e_client, setup, oidc_server, e2e_test_user
):
    """
    Complete SSO authentication flow: configure → get SSO URL → wrong callback → right callback → validate token.

    This test validates:
    1. SSO configuration with OIDC discovery
    2. Getting the SSO authorization URL
    3. Handling invalid authorization codes (error case)
    4. Handling valid authorization codes (success case)
    5. Using the obtained JWT token to create a password (validates token)
    """

    print("\n� Starting complete SSO authentication flow...")

    # Step 1: Configure SSO with the mock OIDC provider
    print("\n📝 Step 1: Configuring SSO provider...")
    configure_response = e2e_client.post(
        "/api/auth/sso/configure",
        json={
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
            "discovery_url": oidc_server["discovery_url"],
        },
    )
    assert configure_response.status_code == 200, (
        f"SSO configuration failed: {configure_response.text}"
    )
    print("✅ SSO configured successfully")

    # Step 2: Get SSO authorization URL
    print("\n🔗 Step 2: Getting SSO authorization URL...")
    url_response = e2e_client.get("/api/auth/sso/url")
    assert url_response.status_code == 200, (
        f"Failed to get SSO URL: {url_response.text}"
    )

    sso_url_data = url_response.json()
    if isinstance(sso_url_data, str):
        sso_url = sso_url_data
    elif isinstance(sso_url_data, dict) and "url" in sso_url_data:
        sso_url = sso_url_data["url"]
    else:
        sso_url = str(sso_url_data)

    assert isinstance(sso_url, str), "SSO URL should be a string"
    assert "http" in sso_url.lower(), "SSO URL should be a valid URL"
    print(f"✅ Got SSO URL: {sso_url}")

    # Step 3: Test wrong callback with invalid authorization code
    print("\n🧪 Step 3: Testing callback with invalid authorization code...")
    invalid_callback_response = e2e_client.get(
        "/api/auth/sso/callback?code=invalid-code-12345"
    )
    assert invalid_callback_response.status_code == 400, (
        f"Expected 400 but got {invalid_callback_response.status_code}"
    )
    error_data = invalid_callback_response.json()
    assert (
        "SSO authentication failed" in error_data["detail"]
        or "invalid" in error_data["detail"].lower()
        or "fail" in error_data["detail"].lower()
    ), f"Expected authentication error, got: {error_data['detail']}"
    print("✅ Invalid code correctly rejected")

    # Step 4: Get valid authorization code by simulating user authorization
    print("\n🔐 Step 4: Simulating user authorization to get valid code...")
    auth_response = httpx.post(
        sso_url,
        data={"sub": e2e_test_user["sub"]},
        follow_redirects=False,
    )
    assert auth_response.status_code in [
        302,
        303,
    ], f"Expected redirect, got {auth_response.status_code}"

    callback_url = auth_response.headers.get("location")
    assert callback_url, "Should have a redirect location"

    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    valid_code = query_params.get("code", [None])[0]
    assert valid_code, f"Authorization code not found in callback URL: {callback_url}"
    print(f"✅ Obtained valid authorization code: {valid_code[:10]}...")

    # Step 5: Test right callback with valid authorization code
    print("\n✨ Step 5: Testing callback with valid authorization code...")
    valid_callback_response = e2e_client.get(
        f"/api/auth/sso/callback?code={valid_code}"
    )
    assert valid_callback_response.status_code == 200, (
        f"Valid callback failed: {valid_callback_response.text}"
    )

    callback_data = valid_callback_response.json()
    assert "message" in callback_data, "Response should contain message"
    assert "user" in callback_data, "Response should contain user info"

    # Extract SSO token from cookie
    sso_token = valid_callback_response.cookies.get("access_token")
    assert sso_token is not None, "access_token cookie should be set"

    user_info = callback_data["user"]

    assert user_info["email"] == e2e_test_user["email"], "Email should match test user"
    assert user_info["display_name"] == e2e_test_user["name"], (
        "Display name should match test user"
    )
    print(f"✅ SSO login successful for {user_info['email']}")

    # Step 6: Validate token by creating a password (this proves the JWT token works)
    print("\n🔑 Step 6: Validating JWT token by creating a password...")

    # Get the user's personal group ID
    me_response = e2e_client.get("/api/users/me")
    assert me_response.status_code == 200
    personal_group_id = me_response.json()["personal_group_id"]

    create_password_response = e2e_client.post(
        "/api/passwords/",
        json={
            "name": "My SSO Test Password",
            "password": "SuperSecure123!@#",
            "folder": "SSO Tests",
            "group_id": personal_group_id,
        },
    )
    assert create_password_response.status_code == 201, (
        f"Failed to create password with SSO token: {create_password_response.text}"
    )

    password_data = create_password_response.json()
    assert password_data["id"] is not None
    print(
        f"✅ JWT token validated successfully! Password created with ID: {password_data['id']}"
    )

    print("\n🎉 Complete SSO authentication flow test passed!")
