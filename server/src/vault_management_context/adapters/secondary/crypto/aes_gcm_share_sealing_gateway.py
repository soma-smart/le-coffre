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
#   key    = HKDF-SHA256(ikm = UTF-8 token, salt = empty, info = HKDF_INFO, 32 bytes)
#   sealed = hex(nonce[12] || AES-256-GCM ciphertext || tag[16]), no associated data
#
# The token is 256 bits of uniform randomness, so HKDF needs no salt and no work
# factor. The lookup hash (SHA-256 of the same token) and this key are
# independent outputs: knowing the lookup hash, as the server does, says
# nothing about the key.
HKDF_INFO = b"le-coffre/vault-share-link/v1"
KEY_BYTES = 32
NONCE_BYTES = 12


class AesGcmShareSealingGateway(ShareSealingGateway):
    def seal(self, share: Share, token: ShareLinkToken) -> str:
        key = HKDF(token.value.encode(), KEY_BYTES, b"", SHA256, context=HKDF_INFO)
        nonce = get_random_bytes(NONCE_BYTES)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(share.secret.encode())
        return (nonce + ciphertext + tag).hex()
