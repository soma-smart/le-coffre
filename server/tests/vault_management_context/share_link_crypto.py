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


def share_link_ack_key(token: str) -> str:
    """What the browser sends to close a share link once the share is saved."""
    return (
        HKDF(algorithm=hashes.SHA256(), length=32, salt=b"", info=b"le-coffre/vault-share-link/ack/v1")
        .derive(token.encode())
        .hex()
    )


def open_sealed_share(sealed_share: str, token: str, setup_id: str, share_index: int) -> str:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"", info=b"le-coffre/vault-share-link/v1").derive(
        token.encode()
    )
    aad = f"le-coffre/vault-share-link/v1|setup_id={setup_id}|share_index={share_index}".encode()
    sealed = bytes.fromhex(sealed_share)
    return AESGCM(key).decrypt(sealed[:12], sealed[12:], aad).decode()


def open_retrieved_share(body: dict, token: str) -> str:
    """Open a retrieve response the way the browser does, with the index it came with."""
    return open_sealed_share(body["sealed_share"], token, body["setup_id"], body["share_index"])


def retrieve_share(client, token: str) -> str:
    """Play a custodian opening their share link, and return the share."""
    response = client.post("/api/vault/share-links/retrieve", json={"lookup_hash": share_link_lookup_hash(token)})
    assert response.status_code == 200, response.text
    return open_retrieved_share(response.json(), token)


def acknowledge_share(client, token: str) -> None:
    """Play a custodian confirming they saved their share, which closes the link."""
    response = client.post(
        "/api/vault/share-links/acknowledge",
        json={"lookup_hash": share_link_lookup_hash(token), "ack_key": share_link_ack_key(token)},
    )
    assert response.status_code == 204, response.text
