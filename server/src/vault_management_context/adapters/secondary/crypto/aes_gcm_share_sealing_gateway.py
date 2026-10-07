from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.Random import get_random_bytes

from vault_management_context.application.gateways import ShareSealingGateway
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import ShareLinkToken

# Wire format, opened by the browser with WebCrypto (frontend
# WebCryptoShareLinkCipher). Any change here is a breaking change there, hence
# the version in the HKDF info string:
#
#   key      = HKDF-SHA256(ikm = UTF-8 token, salt = empty, info = HKDF_INFO, 32 bytes)
#   aad      = UTF-8 "le-coffre/vault-share-link/v1|setup_id=<setup id>|share_index=<index>"
#   sealed   = hex(nonce[12] || AES-256-GCM(key, aad) ciphertext || tag[16])
#   ack key  = HKDF-SHA256(ikm = UTF-8 token, salt = empty, info = ACK_HKDF_INFO, 32 bytes),
#              sent hex encoded by the browser to close the link
#   ack hash = hex(SHA-256(ack key)), what the server stores to check it
#
# The token is 256 bits of uniform randomness, so HKDF needs no salt and no work
# factor. The lookup hash (SHA-256 of the same token) and this key are
# independent outputs: knowing the lookup hash, as the server does, says
# nothing about the key, nor about the ack key.
#
# The associated data binds the ciphertext to the setup and the share index the
# server hands out alongside it: the browser rebuilds it from those two values,
# so a server (or anything in between) relabelling a share makes it fail to open.
HKDF_INFO = b"le-coffre/vault-share-link/v1"
ACK_HKDF_INFO = b"le-coffre/vault-share-link/ack/v1"
KEY_BYTES = 32
NONCE_BYTES = 12


def share_link_aad(setup_id: str, share_index: int) -> bytes:
    return f"{HKDF_INFO.decode()}|setup_id={setup_id}|share_index={share_index}".encode()


class AesGcmShareSealingGateway(ShareSealingGateway):
    def seal(self, share: Share, token: ShareLinkToken, setup_id: str, share_index: int) -> str:
        key = HKDF(token.value.encode(), KEY_BYTES, b"", SHA256, context=HKDF_INFO)
        nonce = get_random_bytes(NONCE_BYTES)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        cipher.update(share_link_aad(setup_id, share_index))
        ciphertext, tag = cipher.encrypt_and_digest(share.secret.encode())
        return (nonce + ciphertext + tag).hex()

    def ack_hash(self, token: ShareLinkToken) -> str:
        ack_key = HKDF(token.value.encode(), KEY_BYTES, b"", SHA256, context=ACK_HKDF_INFO)
        return SHA256.new(ack_key).hexdigest()
