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
