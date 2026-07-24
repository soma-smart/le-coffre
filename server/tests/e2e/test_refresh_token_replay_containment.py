"""
Refresh-token reuse containment (RFC 9700 §4.14.2).

A thief who steals a refresh token and rotates it first wins the race: the
victim's next refresh replays the stolen (now revoked) token. That replay is
the theft signal — the backend must kill every session of the user so the
thief's rotated-forward chain and access token die with it, while the victim
can simply log back in with their password.
"""

import time

ADMIN_CREDENTIALS = {"email": "admin@example.com", "password": "admin-password-123"}


def _register_and_login_admin(client):
    register_response = client.post(
        "/api/auth/register-admin",
        json={**ADMIN_CREDENTIALS, "display_name": "System Administrator"},
    )
    assert register_response.status_code == 201
    login_response = client.post("/api/auth/login", json=ADMIN_CREDENTIALS)
    assert login_response.status_code == 200
    client.refresh_csrf_token()
    return login_response


def test_refresh_token_replay_triggers_containment(e2e_client, client_factory):
    # Victim registers and logs in — their browser holds RT1
    login_response = _register_and_login_admin(e2e_client)
    stolen_refresh_token = login_response.cookies.get("refresh_token")
    assert stolen_refresh_token is not None

    # The thief steals RT1 and rotates it first: RT1 -> RT2 + fresh access token
    attacker_client = client_factory()
    attacker_client.disable_auto_csrf()
    attacker_client.cookies.set("refresh_token", stolen_refresh_token)
    attacker_refresh = attacker_client.post("/api/auth/refresh-token")
    assert attacker_refresh.status_code == 200
    assert attacker_refresh.cookies.get("refresh_token") is not None
    assert attacker_refresh.cookies.get("access_token") is not None

    # The victim's browser replays RT1 — rejected, and the replay of a rotated
    # token triggers containment of the whole session family
    victim_replay = e2e_client.post("/api/auth/refresh-token")
    assert victim_replay.status_code == 400

    # The thief's rotated-forward refresh token is dead
    attacker_second_refresh = attacker_client.post("/api/auth/refresh-token")
    assert attacker_second_refresh.status_code == 400, (
        "the attacker's rotated-forward session must not survive reuse detection"
    )

    # The thief's access token is dead too (session_invalid_before cutoff)
    attacker_me = attacker_client.get("/api/users/me")
    assert attacker_me.status_code == 401, "the attacker's access token must not survive reuse detection"

    # The victim, who knows the password, logs back in and regains access.
    # JWT iat has second precision while the containment cutoff does not — wait
    # out the current second so the fresh tokens are issued strictly after it.
    time.sleep(1.1)
    victim_client = client_factory()
    victim_relogin = victim_client.post("/api/auth/login", json=ADMIN_CREDENTIALS)
    assert victim_relogin.status_code == 200
    victim_client.refresh_csrf_token()
    assert victim_client.get("/api/users/me").status_code == 200
