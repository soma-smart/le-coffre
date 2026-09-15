from uuid import uuid4

from security.csrf_tokens import CsrfTokenManager


def test_should_accept_a_token_it_just_issued():
    manager = CsrfTokenManager()
    user_id = uuid4()

    token = manager.generate_token(user_id)

    assert manager.validate_token(user_id, token) is True


def test_should_keep_earlier_tokens_valid_when_another_is_issued():
    """The multi-tab case, and the reason this file exists.

    One token per user made the app single-tab: every fresh tab fetches a CSRF
    token through the router guard, and the browser extension's approval page
    does the same. Replacing the stored token there invalidated the one every
    other open tab was still holding, so the next POST from an older tab failed
    with "Invalid or expired CSRF token" for no reason the user could see.
    """
    manager = CsrfTokenManager()
    user_id = uuid4()

    first_tab = manager.generate_token(user_id)
    second_tab = manager.generate_token(user_id)

    assert manager.validate_token(user_id, first_tab) is True
    assert manager.validate_token(user_id, second_tab) is True


def test_should_forget_the_oldest_token_once_the_cap_is_reached():
    """Bounded on purpose: the store is in-process and never expires entries."""
    manager = CsrfTokenManager(max_tokens_per_user=3)
    user_id = uuid4()

    oldest = manager.generate_token(user_id)
    kept = [manager.generate_token(user_id) for _ in range(3)]

    assert manager.validate_token(user_id, oldest) is False
    for token in kept:
        assert manager.validate_token(user_id, token) is True


def test_should_refuse_a_token_issued_to_another_user():
    manager = CsrfTokenManager()
    owner, intruder = uuid4(), uuid4()
    token = manager.generate_token(owner)

    assert manager.validate_token(intruder, token) is False


def test_should_refuse_any_token_when_the_user_has_none():
    manager = CsrfTokenManager()

    assert manager.validate_token(uuid4(), "anything") is False


def test_should_drop_every_token_of_a_user_when_deleted():
    manager = CsrfTokenManager()
    user_id = uuid4()
    tokens = [manager.generate_token(user_id) for _ in range(2)]

    manager.delete_token(user_id)

    for token in tokens:
        assert manager.validate_token(user_id, token) is False
