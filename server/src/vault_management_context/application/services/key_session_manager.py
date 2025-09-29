from vault_management_context.application.gateways import (
    EncryptionGateway,
    VaultSessionGateway,
)


class KeySessionManager:
    @staticmethod
    def decrypt_and_store_key(
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
        encrypted_key: str,
        master_key: str,
    ):
        decrypted_key = encryption_gateway.decrypt(encrypted_key, master_key)
        vault_session_gateway.store_decrypted_key(decrypted_key)
