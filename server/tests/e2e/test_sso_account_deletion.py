"""A deleted SSO account loses its access at once.

The SSO identity row used to survive the deletion, and token validation fell
back on it with the roles read from the JWT: a deleted SSO admin kept admin
rights until its access token expired.
"""

from tests.e2e.conftest import authenticate_sso_user, create_sso_user_in_provider

SSO_EMAIL = "sso-admin@example.com"


def test_deleted_sso_admin_cannot_reuse_its_access_token(
    authenticated_admin_client, client_factory, configured_sso, sso_user_factory
):
    sso_user_id = sso_user_factory(SSO_EMAIL, "SSO Admin")["user_id"]
    promoted = authenticated_admin_client.post(f"/api/users/{sso_user_id}/promote-admin")
    assert promoted.status_code == 204, promoted.text

    # Sign in again so the access token itself carries the admin role.
    sso_admin = sso_user_factory(SSO_EMAIL, "SSO Admin")
    sso_admin_client = sso_admin["client"]
    assert sso_admin_client.get("/api/iam/statistics").status_code == 200

    deleted = sso_admin_client.delete(f"/api/users/{sso_user_id}")
    assert deleted.status_code == 204, deleted.text

    replay_client = client_factory()
    replay_client.cookies.set("access_token", sso_admin["token"])
    assert replay_client.get("/api/iam/statistics").status_code == 401
    assert replay_client.get("/api/users/me").status_code == 401


def test_deleted_sso_user_signs_up_again_as_a_new_account(
    authenticated_admin_client, client_factory, configured_sso, sso_user_factory
):
    first_user_id = sso_user_factory(SSO_EMAIL, "SSO User")["user_id"]
    deleted = authenticated_admin_client.delete(f"/api/users/{first_user_id}")
    assert deleted.status_code == 204, deleted.text

    sso_user = create_sso_user_in_provider(configured_sso, SSO_EMAIL, "SSO User")
    second_login = authenticate_sso_user(client_factory(), configured_sso, sso_user)

    assert second_login["user_id"] != first_user_id
    assert authenticated_admin_client.get(f"/api/users/{second_login['user_id']}").status_code == 200
