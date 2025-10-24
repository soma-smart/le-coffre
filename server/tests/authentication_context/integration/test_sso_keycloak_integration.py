import pytest
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from urllib.parse import urlparse, parse_qs

from authentication_context.adapters.secondary import OAuth2SsoGateway


@pytest.fixture
def oauth2_sso_gateway(keycloak_config) -> OAuth2SsoGateway:
    gateway = OAuth2SsoGateway(
        base_url=keycloak_config["keycloak_url"],
        redirect_uri=keycloak_config["redirect_uri"],
    )
    return gateway


@pytest.mark.asyncio
async def test_configure_sso_with_oidc_discovery(oauth2_sso_gateway, keycloak_config):
    # This tests that the OIDC discovery endpoint is accessible and returns valid configuration.

    await oauth2_sso_gateway.configure_with_discovery(
        client_id=keycloak_config["client_id"],
        client_secret=keycloak_config["client_secret"],
        discovery_url=keycloak_config["discovery_url"],
    )

    auth_url = await oauth2_sso_gateway.get_authorize_url()

    assert (
        keycloak_config["keycloak_url"] in auth_url
    ), "Auth URL should contain Keycloak URL"
    assert "redirect_uri=" in auth_url, "Auth URL should contain redirect_uri"
    assert (
        "response_type=code" in auth_url
    ), "Auth URL should use authorization code flow"


@pytest.mark.asyncio
async def test_complete_oauth2_flow_with_browser(oauth2_sso_gateway, keycloak_config):
    # Test complete OAuth2 flow: configure -> authorize -> callback -> token exchange.

    # Step 1: Configure SSO via OIDC discovery
    await oauth2_sso_gateway.configure_with_discovery(
        client_id=keycloak_config["client_id"],
        client_secret=keycloak_config["client_secret"],
        discovery_url=keycloak_config["discovery_url"],
    )

    # Step 2: Get authorization URL
    auth_url = await oauth2_sso_gateway.get_authorize_url()

    # Step 3: Simulate user authentication with Playwright
    auth_code = None
    callback_url = None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Listen for navigation requests to capture the callback URL
            def handle_request(request):
                nonlocal callback_url
                url = request.url
                if "/auth/sso/callback" in url:
                    callback_url = url
                    print(f"✅ Captured callback URL: {url[:80]}...")

            page.on("request", handle_request)

            await page.goto(auth_url, wait_until="networkidle")

            # Wait for login form
            await page.wait_for_selector('input[name="username"]', timeout=15000)

            await page.fill('input[name="username"]', keycloak_config["username"])
            await page.fill('input[name="password"]', keycloak_config["password"])

            await page.click('input[type="submit"]')
            try:
                await page.click('input[type="submit"]')
            except Exception as e:
                # Might fail if redirect happens to unreachable URL
                print(
                    f"   🔹 Click/navigation exception (expected): {type(e).__name__}"
                )

            # Wait for the callback to be intercepted
            for i in range(30):  # Wait up to 15 seconds
                if callback_url:
                    break
                await page.wait_for_timeout(500)

                # Check URL every few iterations
                if i % 4 == 0:
                    current = page.url
                    print(
                        f"   ... still waiting ({i//2}s) - current: {current[:60]}..."
                    )

            if not callback_url:
                # Check current URL in case redirect happened differently
                current_url = page.url
                print(f"   ⚠️  No callback intercepted. Current URL: {current_url}")

                # Check if we're on an error page
                page_content = await page.content()
                print(f"   Page title: {await page.title()}")

                # Look for specific error messages
                if "invalid" in page_content.lower() or "error" in page_content.lower():
                    print(f"   ❌ Error detected in page")
                    # Print visible text
                    visible_text = await page.locator("body").inner_text()
                    print(f"   Visible text: {visible_text[:500]}")
                    raise Exception(
                        f"Keycloak login/authorization failed: {visible_text[:200]}"
                    )
                elif "chrome-error" in current_url or "about:" in current_url:
                    pytest.fail(
                        f"❌ Redirect failed - check Keycloak client configuration"
                    )
                else:
                    pytest.fail(f"❌ Expected callback redirect, got: {current_url}")

            await browser.close()

        # Parse authorization code
        parsed = urlparse(callback_url)
        query_params = parse_qs(parsed.query)
        auth_code = query_params.get("code", [None])[0]

        if not auth_code:
            # Check for error in callback
            error = query_params.get("error", [None])[0]
            error_description = query_params.get("error_description", [None])[0]
            if error:
                pytest.fail(f"❌ OAuth error: {error} - {error_description}")
            else:
                pytest.fail(f"❌ Authorization code not found in URL: {callback_url}")

    except PlaywrightTimeoutError as e:
        pytest.fail(f"❌ Playwright timeout: {e}")
    except Exception as e:
        pytest.fail(f"❌ Browser automation error: {e}")

    # Step 4: Exchange authorization code for tokens
    sso_user = await oauth2_sso_gateway.validate_callback(auth_code)

    # Verify SSO user data
    assert (
        sso_user.email == keycloak_config["email"]
    ), f"Email mismatch: expected {keycloak_config['email']}, got {sso_user.email}"
    assert sso_user.display_name is not None, "Display name should be set"
    assert sso_user.sso_user_id is not None, "SSO user ID should be set"
    assert sso_user.sso_provider is not None, "SSO provider should be set"


@pytest.mark.asyncio
async def test_oauth2_flow_with_invalid_code(oauth2_sso_gateway, keycloak_config):
    # Test that invalid authorization code is rejected.
    await oauth2_sso_gateway.configure_with_discovery(
        client_id=keycloak_config["client_id"],
        client_secret=keycloak_config["client_secret"],
        discovery_url=keycloak_config["discovery_url"],
    )

    with pytest.raises(Exception) as exc_info:
        await oauth2_sso_gateway.validate_callback("invalid-code-xyz123")

    # The exception should indicate authentication failure
    error_message = str(exc_info.value).lower()
    assert (
        "invalid" in error_message
        or "fail" in error_message
        or "error" in error_message
    )


@pytest.mark.asyncio
async def test_oidc_discovery_with_invalid_url(oauth2_sso_gateway):
    # Test that invalid discovery URL fails gracefully.
    with pytest.raises(Exception) as exc_info:
        await oauth2_sso_gateway.configure_with_discovery(
            client_id="test-client",
            client_secret="test-secret",
            discovery_url="https://invalid-domain-xyz123.com/.well-known/openid-configuration",
        )
