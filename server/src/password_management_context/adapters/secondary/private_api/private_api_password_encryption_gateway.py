from password_management_context.application.gateways import (
    PasswordEncryptionGateway,
)
from vault_management_context.adapters.primary.private_api import EncryptionApi


class PrivateApiPasswordEncryptionGateway(PasswordEncryptionGateway):
    """Gateway that wraps vault management's EncryptionApi for password encryption"""

    def __init__(self, encryption_api: EncryptionApi):
        self._encryption_api = encryption_api

    def encrypt(self, password: str) -> str:
        """Encrypts the given password using vault management's encryption service"""
        return self._encryption_api.encrypt(password)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts the given ciphertext using vault management's encryption service"""
        return self._encryption_api.decrypt(ciphertext)
