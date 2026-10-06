"""The sealed share is opened by the browser, not by the server.

These tests open it with an independent implementation (the `cryptography`
package, mirroring what WebCrypto does in the frontend) rather than with the
adapter itself, so they pin the wire format and not merely a round trip.
"""

import pytest
from cryptography.exceptions import InvalidTag

from tests.vault_management_context.share_link_crypto import open_sealed_share
from vault_management_context.adapters.secondary import AesGcmShareSealingGateway
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import ShareLinkToken

# Shared with frontend/src/infrastructure/crypto/__tests__/WebCryptoShareLinkCipher.spec.ts:
# both sides must open this exact vector.
VECTOR_TOKEN = "BK5Zz4OJPJKwTdNlQD4Ba46oFHyldr_lhe62p2k0Kuk"
VECTOR_LOOKUP_HASH = "c3fa2ef905648d4512865127c8555921bb7a5de5eeb48ba9bebfe60627155ed0"
VECTOR_SEALED = "4493671aec14476af1126378713a0e869cb569b5ae0df45d6a917c8fda69fb59cbc3877831ca7a2155c6ffe9a6ae66891214a677a1628103e6c250987f1a"
VECTOR_SHARE = "3:5f1c0a9e2b7d4c6e8a1f3b5d7c9e0a2b"


@pytest.fixture
def gateway():
    return AesGcmShareSealingGateway()


def test_sealed_share_opens_with_the_token_through_an_independent_implementation(gateway):
    token = ShareLinkToken.generate()
    share = Share("2:00112233445566778899aabbccddeeff")

    assert open_sealed_share(gateway.seal(share, token), token.value) == share.secret


def test_sealed_share_does_not_contain_the_share_in_clear(gateway):
    share = Share("2:00112233445566778899aabbccddeeff")
    sealed = gateway.seal(share, ShareLinkToken.generate())

    assert share.secret not in sealed
    assert share.secret.split(":")[1] not in sealed


def test_sealed_share_cannot_be_opened_with_another_token(gateway):
    sealed = gateway.seal(Share("1:aa"), ShareLinkToken.generate())

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed, ShareLinkToken.generate().value)


def test_sealed_share_cannot_be_opened_with_the_lookup_hash(gateway):
    # The lookup hash is all the server keeps; it must not double as the key.
    token = ShareLinkToken.generate()
    sealed = gateway.seal(Share("1:aa"), token)

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed, token.lookup_hash())


def test_tampered_sealed_share_is_rejected(gateway):
    token = ShareLinkToken.generate()
    sealed = bytearray.fromhex(gateway.seal(Share("1:aa"), token))
    sealed[-1] ^= 0x01

    with pytest.raises(InvalidTag):
        open_sealed_share(sealed.hex(), token.value)


def test_sealing_twice_uses_a_fresh_nonce(gateway):
    token = ShareLinkToken.generate()
    first = gateway.seal(Share("1:aa"), token)
    second = gateway.seal(Share("1:aa"), token)

    assert first[:24] != second[:24]


def test_reference_vector_shared_with_the_frontend_still_opens():
    assert ShareLinkToken(VECTOR_TOKEN).lookup_hash() == VECTOR_LOOKUP_HASH
    assert open_sealed_share(VECTOR_SEALED, VECTOR_TOKEN) == VECTOR_SHARE
