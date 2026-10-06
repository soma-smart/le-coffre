"""Open share links the way the browser does (see frontend WebCryptoShareLinkCipher).

Deliberately written against the `cryptography` package rather than the
production adapter, so tests pin the wire format instead of a round trip.
"""

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def share_link_lookup_hash(token: str) -> str:
    """What the browser sends to address a share link: never the token itself."""
    return hashlib.sha256(token.encode()).hexdigest()


def open_sealed_share(sealed_share: str, token: str) -> str:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"", info=b"le-coffre/vault-share-link/v1").derive(
        token.encode()
    )
    sealed = bytes.fromhex(sealed_share)
    return AESGCM(key).decrypt(sealed[:12], sealed[12:], None).decode()


def retrieve_share(client, token: str) -> str:
    """Play a custodian opening their share link, and return the share."""
    response = client.post("/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash(token)})
    assert response.status_code == 200, response.text
    return open_sealed_share(response.json()["sealed_share"], token)
