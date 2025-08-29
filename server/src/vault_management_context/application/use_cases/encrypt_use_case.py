from vault_management_context.application.gateways import (
    EncryptionGateway,
    VaultSessionGateway,
)


class EncryptUseCase:
    def __init__(
        self,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
    ):
        self.encryption_gateway = encryption_gateway
        self.vault_session_gateway = vault_session_gateway

    def execute(self, decrypted_data: str) -> str:
        decryption_key = self.vault_session_gateway.get_decrypted_key()
        return self.encryption_gateway.encrypt(decrypted_data, decryption_key)
