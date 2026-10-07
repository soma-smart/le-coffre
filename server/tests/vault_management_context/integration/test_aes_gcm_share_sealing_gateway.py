"""The sealed share is opened by the browser, not by the server.

These tests open it with an independent implementation (the `cryptography`
package, mirroring what WebCrypto does in the frontend) rather than with the
adapter itself, so they pin the wire format and not merely a round trip.
"""

import pytest
from cryptography.exceptions import InvalidTag

from tests.vault_management_context.share_link_crypto import open_sealed_share, share_link_ack_key
from vault_management_context.adapters.secondary import AesGcmShareSealingGateway
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import ShareLinkToken

# Shared with frontend/src/infrastructure/crypto/__tests__/WebCryptoShareLinkCipher.spec.ts:
# both sides must open this exact vector.
VECTOR_TOKEN = "BK5Zz4OJPJKwTdNlQD4Ba46oFHyldr_lhe62p2k0Kuk"
VECTOR_LOOKUP_HASH = "c3fa2ef905648d4512865127c8555921bb7a5de5eeb48ba9bebfe60627155ed0"
VECTOR_SETUP_ID = "0b6c2c8e-3f5a-4c1e-9d7b-2a1f4e8c9d01"
VECTOR_SHARE_INDEX = 3
VECTOR_SEALED = "59f59abb863506f04c654a769fb5a1ef5fd889383c799ae9917d314034208919e86f5eeabbbc141dfc8d2c9802f8b0f08b793dcc1a186fc3d43191ae71fa"
VECTOR_SHARE = "3:5f1c0a9e2b7d4c6e8a1f3b5d7c9e0a2b"
VECTOR_ACK_KEY = "98f5d69fb3a34b714e9adfc4893dfcd3a8ebca27938253505fadcc3a154153b2"
VECTOR_ACK_HASH = "874d23f3e0ae538b0bc80a6c969a700fe49969ea281fcd451ea7aec4bfb8b09e"


@pytest.fixture
def gateway():
    return AesGcmShareSealingGateway()


SETUP_ID = "setup-1"


def _seal(gateway, share: Share, token: ShareLinkToken, share_index: int = 1) -> str:
    return gateway.seal(share, token, SETUP_ID, share_index)


def test_sealed_share_opens_with_the_token_through_an_independent_implementation(gateway):
    token = ShareLinkToken.generate()
    share = Share("2:00112233445566778899aabbccddeeff")

    assert open_sealed_share(_seal(gateway, share, token, 2), token.value, SETUP_ID, 2) == share.secret


def test_sealed_share_does_not_contain_the_share_in_clear(gateway):
    share = Share("2:00112233445566778899aabbccddeeff")
    sealed = _seal(gateway, share, ShareLinkToken.generate())

    assert share.secret not in sealed
    assert share.secret.split(":")[1] not in sealed


def test_sealed_share_cannot_be_opened_with_another_token(gateway):
    sealed = _seal(gateway, Share("1:aa"), ShareLinkToken.generate())

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed, ShareLinkToken.generate().value, SETUP_ID, 1)


def test_sealed_share_cannot_be_opened_with_the_lookup_hash(gateway):
    # The lookup hash is all the server keeps; it must not double as the key.
    token = ShareLinkToken.generate()
    sealed = _seal(gateway, Share("1:aa"), token)

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed, token.lookup_hash(), SETUP_ID, 1)


def test_tampered_sealed_share_is_rejected(gateway):
    token = ShareLinkToken.generate()
    sealed = bytearray.fromhex(_seal(gateway, Share("1:aa"), token))
    sealed[-1] ^= 0x01

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed.hex(), token.value, SETUP_ID, 1)


@pytest.mark.parametrize(
    ("setup_id", "share_index"),
    [(SETUP_ID, 2), ("another-setup", 1), ("", 1)],
    ids=["other index", "other setup", "no setup"],
)
def test_sealed_share_does_not_open_under_another_setup_or_index(gateway, setup_id, share_index):
    # Whatever relabels the share between sealing and opening breaks the tag.
    token = ShareLinkToken.generate()
    sealed = _seal(gateway, Share("1:aa"), token, share_index=1)

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed, token.value, setup_id, share_index)


def test_sealing_twice_uses_a_fresh_nonce(gateway):
    token = ShareLinkToken.generate()
    first = _seal(gateway, Share("1:aa"), token)
    second = _seal(gateway, Share("1:aa"), token)

    assert first[:24] != second[:24]


def test_reference_vector_shared_with_the_frontend_still_opens():
    assert ShareLinkToken(VECTOR_TOKEN).lookup_hash() == VECTOR_LOOKUP_HASH
    assert open_sealed_share(VECTOR_SEALED, VECTOR_TOKEN, VECTOR_SETUP_ID, VECTOR_SHARE_INDEX) == VECTOR_SHARE


def test_ack_hash_is_the_sha256_of_the_ack_key_the_browser_derives(gateway):
    token = ShareLinkToken(VECTOR_TOKEN)

    assert share_link_ack_key(VECTOR_TOKEN) == VECTOR_ACK_KEY
    assert gateway.ack_hash(token) == VECTOR_ACK_HASH


def test_ack_hash_is_neither_the_lookup_hash_nor_derivable_from_it(gateway):
    token = ShareLinkToken.generate()

    assert gateway.ack_hash(token) != token.lookup_hash()
    assert share_link_ack_key(token.value) != token.lookup_hash()
