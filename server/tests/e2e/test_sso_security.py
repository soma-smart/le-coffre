from urllib.parse import parse_qs, urlparse


def _extract_sso_url(response) -> str:
    data = response.json()
    return data if isinstance(data, str) else str(data)


def test_sso_url_sets_state_cookie_matching_the_url(e2e_client, configured_sso):
    response = e2e_client.get("/api/auth/sso/url")
    assert response.status_code == 200

    state_in_url = parse_qs(urlparse(_extract_sso_url(response)).query).get("state", [None])[0]
    assert state_in_url, "authorization URL must carry a state parameter"
    assert e2e_client.cookies.get("sso_state") == state_in_url


def test_sso_callback_without_state_is_rejected(e2e_client, configured_sso):
    e2e_client.get("/api/auth/sso/url")  # sets the sso_state cookie

    response = e2e_client.get("/api/auth/sso/callback?code=anything")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid SSO state"


def test_sso_callback_with_mismatched_state_is_rejected(e2e_client, configured_sso):
    e2e_client.get("/api/auth/sso/url")  # sets the sso_state cookie

    response = e2e_client.get("/api/auth/sso/callback?code=anything&state=forged-state")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid SSO state"


_CONFIGURE_BODY = {
    "client_id": "x",
    "client_secret": "x",
    "discovery_url": "https://idp.example.com/.well-known/openid-configuration",
}


def test_sso_configure_requires_a_csrf_token(authenticated_admin_client):
    # SSO routes are no longer blanket CSRF-exempt: the authenticated admin POST
    # must carry X-CSRF-Token (defense in depth on top of SameSite=strict).
    authenticated_admin_client.disable_auto_csrf()
    try:
        response = authenticated_admin_client.post("/api/auth/sso/configure", json=_CONFIGURE_BODY)
    finally:
        authenticated_admin_client.enable_auto_csrf()

    assert response.status_code == 403
    assert "CSRF token missing" in response.json()["detail"]


def test_sso_configure_without_auth_still_returns_401(unauthenticated_client):
    # Unchanged behaviour: with no session there is no CSRF token to check, so the
    # middleware defers and the route answers 401 (not 403).
    response = unauthenticated_client.post("/api/auth/sso/configure", json=_CONFIGURE_BODY)

    assert response.status_code == 401
