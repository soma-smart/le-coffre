from password_management_context.application.gateways import (
    PasswordEncryptionGateway,
)
from password_management_context.domain.exceptions import PasswordEncryptionUnavailableError
from vault_management_context.adapters.primary.private_api import EncryptionApi
from vault_management_context.domain.exceptions import VaultManagementDomainError


class PrivateApiPasswordEncryptionGateway(PasswordEncryptionGateway):
    """Gateway that wraps vault management's EncryptionApi for password encryption"""

    def __init__(self, encryption_api: EncryptionApi):
        self._encryption_api = encryption_api

    def encrypt(self, password: str) -> str:
        """Encrypts the given password using vault management's encryption service"""
        try:
            return self._encryption_api.encrypt(password)
        except VaultManagementDomainError as e:
            raise PasswordEncryptionUnavailableError() from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts the given ciphertext using vault management's encryption service"""
        try:
            return self._encryption_api.decrypt(ciphertext)
        except VaultManagementDomainError as e:
            raise PasswordEncryptionUnavailableError() from e
