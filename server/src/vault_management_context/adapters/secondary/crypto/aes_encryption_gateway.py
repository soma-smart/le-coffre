from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

from vault_management_context.application.gateways import EncryptionGateway


class AesEncryptionGateway(EncryptionGateway):
    def generate_vault_key(self, master_key: str) -> str:
        """Generate a random vault key and encrypt it using the master key"""
        # Generate a 32-byte (256-bit) vault key
        vault_key = get_random_bytes(32).hex()

        return self.encrypt(vault_key, master_key)

    def encrypt(self, decrypted_data: str, master_key: str) -> str:
        # Generate a random salt for key derivation
        salt = get_random_bytes(16)

        cipher = self._get_cipher(master_key, salt)

        # Encrypt the data
        bytes_decrypted_data = decrypted_data.encode("utf-8")
        ciphertext, auth_tag = cipher.encrypt_and_digest(bytes_decrypted_data)

        # Combine salt + nonce + auth_tag + ciphertext
        encrypted_data = salt + cipher.nonce + auth_tag + ciphertext

        return encrypted_data.hex()

    def decrypt(self, encrypted_data: str, master_key: str) -> str:
        """Decrypt a key using the master key"""
        bytes_encrypted_data = bytes.fromhex(encrypted_data)

        salt = bytes_encrypted_data[:16]
        nonce = bytes_encrypted_data[16:32]
        auth_tag = bytes_encrypted_data[32:48]
        ciphertext = bytes_encrypted_data[48:]

        cipher = self._get_cipher(master_key, salt, nonce)

        try:
            decrypted_data = cipher.decrypt_and_verify(ciphertext, auth_tag)
            return decrypted_data.decode("utf-8")
        except ValueError as e:
            raise ValueError(f"Failed to decrypt vault key: {e}") from e

    def _get_cipher(self, master_key, salt, nonce: bytes | None = None):
        # Derive the same key using PBKDF2
        derived_key = PBKDF2(master_key, salt, 32, count=100000)

        # Create AES cipher in GCM mod
        if nonce:
            return AES.new(derived_key, AES.MODE_GCM, nonce=nonce)
        return AES.new(derived_key, AES.MODE_GCM)
