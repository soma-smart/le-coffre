from vault_management_context.application.gateways.encryption_gateway import (
    EncryptionGateway,
)


class FakeEncryptionGateway(EncryptionGateway):
    def __init__(self):
        self._encrypted_data = None
        self._decrypted_data = None
        self._master_key = None

    def set_encrypted_data(self, encrypted_data: str) -> None:
        self._encrypted_data = encrypted_data

    def set_decrypted_data(self, decrypted_data: str) -> None:
        self._decrypted_data = decrypted_data

    def set_master_key(self, master_key: str) -> None:
        self._master_key = master_key

    def generate_vault_key(self, master_key: str) -> str:
        if self._encrypted_data is None or self._master_key != master_key:
            raise ValueError("No encrypted data configured for fake")
        return self._encrypted_data

    def encrypt(self, decrypted_data: str, master_key: str) -> str:
        if self._encrypted_data is None or self._decrypted_data != decrypted_data or self._master_key != master_key:
            raise ValueError("Decrypted data does not match configured value")
        return self._encrypted_data

    def decrypt(self, encrypted_data: str, master_key: str) -> str:
        if self._decrypted_data is None or self._encrypted_data != encrypted_data or self._master_key != master_key:
            raise ValueError("Encrypted data does not match configured value")
        return self._decrypted_data
