import logging
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


def test_is_configured_is_anonymous_and_leaks_only_the_boolean(unauthenticated_client, configured_sso):
    # The login page calls this before the user authenticates, so the
    # endpoint is intentionally reachable without an access_token cookie. Crucially,
    # even with SSO configured the anonymous response is a single boolean and never
    # the discovery URL, client ID or any IdP endpoint.
    response = unauthenticated_client.get("/api/auth/sso/is-configured")

    assert response.status_code == 200
    assert response.json() == {"is_set": True}


def test_is_configured_reports_false_anonymously_when_unset(unauthenticated_client):
    # Same anonymous contract with no SSO configured: 200 and only the boolean.
    response = unauthenticated_client.get("/api/auth/sso/is-configured")

    assert response.status_code == 200
    assert response.json() == {"is_set": False}


# The 400 body is deliberately generic in every rejection case, so an operator
# reading it cannot tell a client that dropped its cookie jar (the CLI failure
# mode) from a genuine forged state. Discriminate in the server log instead —
# never in the response, and never by echoing the state itself, which is a CSRF
# token.
_SSO_CALLBACK_LOGGER = "identity_access_management_context.adapters.primary.fastapi.routes.sso.sso_callback_route"


def test_given_no_state_cookie_when_calling_callback_should_log_the_missing_cookie_reason(
    e2e_client, configured_sso, caplog
):
    url_response = e2e_client.get("/api/auth/sso/url")
    state = parse_qs(urlparse(_extract_sso_url(url_response)).query)["state"][0]
    e2e_client.cookies.delete("sso_state")  # the client did not keep the jar

    with caplog.at_level(logging.WARNING, logger=_SSO_CALLBACK_LOGGER):
        response = e2e_client.get(f"/api/auth/sso/callback?code=anything&state={state}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid SSO state"
    assert "sso_state cookie missing" in caplog.text
    assert state not in caplog.text, "the state is a CSRF token and must never be logged"


def test_given_mismatched_state_when_calling_callback_should_log_the_mismatch_reason(
    e2e_client, configured_sso, caplog
):
    e2e_client.get("/api/auth/sso/url")  # sets the sso_state cookie

    with caplog.at_level(logging.WARNING, logger=_SSO_CALLBACK_LOGGER):
        response = e2e_client.get("/api/auth/sso/callback?code=anything&state=forged-state")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid SSO state"
    assert "state mismatch" in caplog.text
    assert "forged-state" not in caplog.text


def test_given_no_state_parameter_when_calling_callback_should_log_the_missing_parameter_reason(
    e2e_client, configured_sso, caplog
):
    e2e_client.get("/api/auth/sso/url")  # sets the sso_state cookie

    with caplog.at_level(logging.WARNING, logger=_SSO_CALLBACK_LOGGER):
        response = e2e_client.get("/api/auth/sso/callback?code=anything")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid SSO state"
    assert "state query parameter missing" in caplog.text
