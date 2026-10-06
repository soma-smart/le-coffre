import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from vault_management_context.domain.entities import SHARE_LINK_LIFETIME, ShareLink
from vault_management_context.domain.exceptions import (
    InvalidShareLinkLookupError,
    ShareLinkUnusableError,
)
from vault_management_context.domain.value_objects import ShareLinkLookupHash, ShareLinkToken

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def _link() -> ShareLink:
    return ShareLink.create(setup_id="s", share_index=1, lookup_hash="0" * 64, sealed_share="sealed", now=NOW)


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


@pytest.mark.parametrize("value", ["", "f" * 63, "f" * 65, "F" * 64, "g" * 64, " " + "f" * 63])
def test_lookup_hash_rejects_anything_but_a_sha256_hex_digest(value):
    with pytest.raises(InvalidShareLinkLookupError):
        ShareLinkLookupHash(value)


def test_lookup_hash_accepts_a_sha256_hex_digest():
    digest = hashlib.sha256(b"x").hexdigest()
    assert ShareLinkLookupHash(digest).value == digest


def test_link_is_usable_until_48_hours_then_expired():
    link = _link()
    link.ensure_not_expired(NOW + timedelta(hours=47, minutes=59))
    assert not link.is_expired(NOW + timedelta(hours=47, minutes=59))

    assert link.is_expired(NOW + timedelta(hours=48))
    with pytest.raises(ShareLinkUnusableError):
        link.ensure_not_expired(NOW + timedelta(hours=48))
