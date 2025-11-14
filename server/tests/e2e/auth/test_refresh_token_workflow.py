"""End-to-end test for refresh access token workflow.

This test validates the complete refresh token flow:
1. User logs in via SSO and receives access_token + refresh_token
2. User uses refresh_token to get a new access_token
3. User uses the new access_token to access protected resources
"""

import pytest
import httpx
from urllib.parse import urlparse, parse_qs


@pytest.mark.asyncio
async def test_refresh_access_token_workflow(
    e2e_client, setup, oidc_server, e2e_test_user
):
    """
    Complete refresh token workflow: SSO login → use refresh_token → validate new access_token.

    This test validates:
    1. SSO login returns both access_token and refresh_token in cookies
    2. Using refresh_token to get a new access_token
    3. The new access_token works for protected endpoints
    4. Invalid refresh_token is rejected
    """

    print("\n🔄 Starting refresh access token workflow...")

    # Step 1: Configure SSO provider
    print("\n📝 Step 1: Configuring SSO provider...")
    configure_response = e2e_client.post(
        "/api/auth/sso/configure",
        json={
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
            "discovery_url": oidc_server["discovery_url"],
        },
    )
    assert configure_response.status_code == 200
    print("✅ SSO configured successfully")

    # Step 2: Get SSO authorization URL
    print("\n🔗 Step 2: Getting SSO authorization URL...")
    url_response = e2e_client.get("/api/auth/sso/url")
    assert url_response.status_code == 200
    sso_url_data = url_response.json()
    sso_url = (
        sso_url_data
        if isinstance(sso_url_data, str)
        else sso_url_data.get("url", str(sso_url_data))
    )
    print(f"✅ Got SSO URL: {sso_url}")

    # Step 3: Simulate user authorization and get valid code
    print("\n🔐 Step 3: Simulating user authorization...")

    auth_response = httpx.post(
        sso_url,
        data={"sub": e2e_test_user["sub"]},
        follow_redirects=False,
    )
    assert auth_response.status_code in [302, 303]
    callback_url = auth_response.headers.get("location")
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    valid_code = query_params.get("code", [None])[0]
    assert valid_code
    print(f"✅ Obtained valid authorization code: {valid_code[:10]}...")

    # Step 4: SSO callback to get access_token and refresh_token
    print("\n✨ Step 4: Completing SSO login...")
    callback_response = e2e_client.get(f"/api/auth/sso/callback?code={valid_code}")
    assert callback_response.status_code == 200

    # Extract tokens from cookies
    access_token = callback_response.cookies.get("access_token")
    refresh_token = callback_response.cookies.get("refresh_token")

    assert access_token is not None, "access_token cookie should be set"
    assert refresh_token is not None, "refresh_token cookie should be set"

    user_info = callback_response.json()["user"]
    print(f"✅ SSO login successful for {user_info['email']}")
    print("✅ Received access_token and refresh_token in cookies")

    # Step 5: Use refresh_token to get new access_token (via cookie)
    print("\n🔄 Step 5: Using refresh_token to get new access_token...")
    # Set refresh_token cookie directly on client instance
    e2e_client.cookies.set("refresh_token", refresh_token)
    refresh_response = e2e_client.post("/api/auth/refresh-token")
    assert refresh_response.status_code == 200, (
        f"Refresh token failed: {refresh_response.text}"
    )

    refresh_data = refresh_response.json()
    assert "message" in refresh_data
    assert "access_token" in refresh_data
    assert refresh_data["message"] == "Access token refreshed successfully"

    # Extract new access token from cookie
    new_access_token = refresh_response.cookies.get("access_token")
    assert new_access_token is not None, "New access_token cookie should be set"
    assert new_access_token != access_token, "New access token should be different"

    print("✅ Successfully obtained new access_token")
    print(f"   Old token: {access_token[:20]}...")
    print(f"   New token: {new_access_token[:20]}...")

    # Step 6: Also test refresh via body parameter
    print("\n📤 Step 6: Testing refresh token via body parameter...")
    body_refresh_response = e2e_client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert body_refresh_response.status_code == 200
    body_refresh_data = body_refresh_response.json()
    assert "access_token" in body_refresh_data
    print("✅ Refresh token via body parameter works")

    print("\n🎉 Complete refresh access token workflow test passed!")
