import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from vault_management_context.domain.entities import SHARE_LINK_LIFETIME, SHARE_LINK_REOPEN_WINDOW, ShareLink
from vault_management_context.domain.exceptions import InvalidShareLinkLookupError, ShareLinkAckRejectedError
from vault_management_context.domain.value_objects import ShareLinkAckKey, ShareLinkLookupHash, ShareLinkToken

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
ACK_KEY = bytes(range(32))


def _link() -> ShareLink:
    return ShareLink.create(
        setup_id="s",
        share_index=1,
        lookup_hash="0" * 64,
        ack_hash=hashlib.sha256(ACK_KEY).hexdigest(),
        sealed_share="sealed",
        now=NOW,
    )


def test_share_link_lifetime_is_48_hours():
    assert SHARE_LINK_LIFETIME == timedelta(hours=48)
    assert _link().expires_at == NOW + timedelta(hours=48)


def test_token_lookup_hash_is_the_sha256_of_the_token():
    token = ShareLinkToken.generate()
    assert token.lookup_hash() == hashlib.sha256(token.value.encode()).hexdigest()


def test_generated_tokens_carry_256_bits_and_are_unique():
    tokens = {ShareLinkToken.generate().value for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(value) >= 43 for value in tokens)


def test_token_never_shows_its_value_when_printed():
    token = ShareLinkToken.generate()
    assert token.value not in str(token)
    assert token.value not in repr(token)


@pytest.mark.parametrize("value", ["", "f" * 63, "f" * 65, "F" * 64, "g" * 64, " " + "f" * 63, "f" * 64 + "\n"])
def test_lookup_hash_rejects_anything_but_a_sha256_hex_digest(value):
    with pytest.raises(InvalidShareLinkLookupError):
        ShareLinkLookupHash(value)


def test_lookup_hash_accepts_a_sha256_hex_digest():
    digest = hashlib.sha256(b"x").hexdigest()
    assert ShareLinkLookupHash(digest).value == digest


def test_link_is_usable_until_48_hours_then_expired():
    link = _link()
    assert link.can_be_delivered(NOW + timedelta(hours=47, minutes=59))
    assert not link.is_expired(NOW + timedelta(hours=47, minutes=59))

    assert link.is_expired(NOW + timedelta(hours=48))
    assert not link.can_be_delivered(NOW + timedelta(hours=48))
    assert link.is_purgeable(NOW + timedelta(hours=48))


def test_reopen_window_is_15_minutes():
    assert SHARE_LINK_REOPEN_WINDOW == timedelta(minutes=15)


def test_delivered_link_can_be_reopened_until_its_window_ends():
    link = _link()
    link.delivered_at = NOW
    link.reopenable_until = NOW + SHARE_LINK_REOPEN_WINDOW

    assert link.can_be_delivered(NOW + timedelta(minutes=14, seconds=59))
    assert not link.can_be_delivered(NOW + SHARE_LINK_REOPEN_WINDOW)
    assert link.is_purgeable(NOW + SHARE_LINK_REOPEN_WINDOW)


def test_reopen_window_does_not_outlive_the_link():
    link = _link()
    link.delivered_at = link.expires_at - timedelta(minutes=5)
    link.reopenable_until = link.delivered_at + SHARE_LINK_REOPEN_WINDOW

    assert not link.can_be_delivered(link.expires_at)


def test_link_accepts_only_the_ack_key_matching_its_hash():
    link = _link()
    assert link.accepts_ack(ACK_KEY)
    assert not link.accepts_ack(bytes(32))


@pytest.mark.parametrize("value", ["", "f" * 63, "f" * 65, "F" * 64, "g" * 64, "f" * 64 + "\n"])
def test_ack_key_rejects_anything_but_256_bits_of_hex(value):
    with pytest.raises(ShareLinkAckRejectedError):
        ShareLinkAckKey(value)


def test_ack_key_never_shows_its_value_when_printed():
    assert "ab" * 32 not in repr(ShareLinkAckKey("ab" * 32))
