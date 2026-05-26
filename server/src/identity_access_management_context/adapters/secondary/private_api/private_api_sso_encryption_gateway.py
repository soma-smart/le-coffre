from identity_access_management_context.application.gateways import (
    SsoEncryptionGateway,
)
from identity_access_management_context.domain.exceptions import SsoEncryptionUnavailableError
from vault_management_context.adapters.primary.private_api import EncryptionApi
from vault_management_context.domain.exceptions import VaultManagementDomainError


class PrivateApiSsoEncryptionGateway(SsoEncryptionGateway):
    """Gateway that wraps vault management's EncryptionApi for SSO encryption"""

    def __init__(self, encryption_api: EncryptionApi):
        self._encryption_api = encryption_api

    def encrypt(self, plaintext: str) -> str:
        """Encrypts the given plaintext using vault management's encryption service"""
        try:
            return self._encryption_api.encrypt(plaintext)
        except VaultManagementDomainError as e:
            raise SsoEncryptionUnavailableError() from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts the given ciphertext using vault management's encryption service"""
        try:
            return self._encryption_api.decrypt(ciphertext)
        except VaultManagementDomainError as e:
            raise SsoEncryptionUnavailableError() from e
