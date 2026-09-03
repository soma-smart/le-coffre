import pytest

from security.log_paths import sanitize_path_for_log


@pytest.mark.parametrize(
    "path",
    [
        "/api/passwords/0f8c1e2a-1111-2222-3333-444455556666",
        "/api/passwords/a1b2c3d4-1111-2222-3333-444455556666",
        "/api/groups/0f8c1e2a-1111-2222-3333-444455556666",
        "/api/extension/tokens/0f8c1e2a-1111-2222-3333-444455556666",
    ],
)
def test_should_drop_a_uuid_wherever_it_sits(path):
    """The regression.

    The previous helper truncated to three segments, which keeps the id of
    every `/api/<resource>/<id>` route: the id *is* the third segment. It
    promised in its own docstring that resource IDs never reach the log, and
    logged them.
    """
    sanitized = sanitize_path_for_log(path)

    assert "0f8c1e2a" not in sanitized
    assert "a1b2c3d4" not in sanitized
    assert sanitized.endswith("/*")


def test_should_drop_a_pairing_code_without_losing_the_operation():
    # A fixed truncation had to choose between keeping the code and keeping
    # `approve`. Redacting by shape keeps the route and drops the value.
    assert sanitize_path_for_log("/api/extension/pairing/K7QM-3XR9/approve") == ("/api/extension/pairing/*/approve")


@pytest.mark.parametrize(
    "path",
    [
        "/api/users/me",
        "/api/auth/csrf-token",
        "/api/auth/register-admin",
        "/api/one-time-links/consume",
        "/api/vault/validate-setup",
        "/api/extension/device/exchange",
        "/api/passwords/list",
    ],
)
def test_should_keep_a_route_made_only_of_static_segments(path):
    assert sanitize_path_for_log(path) == path


def test_should_survive_a_root_or_trailing_slash():
    assert sanitize_path_for_log("/") == "/"
    assert sanitize_path_for_log("/api/passwords/") == "/api/passwords"


def test_should_redact_anything_it_does_not_recognise_as_a_route_word():
    # Conservative on purpose: an unfamiliar segment is dropped rather than
    # logged, so a value never rides along because nobody updated this module.
    assert sanitize_path_for_log("/api/UPPER/x_y/verylongsegmentthatgoesonandonandon") == "/api/*/*/*"
