from vault_management_context.application.commands import DecryptCommand
from vault_management_context.application.gateways import (
    EncryptionGateway,
    VaultSessionGateway,
)


from shared_kernel.application.tracing import TracedUseCase


class DecryptUseCase(TracedUseCase):
    def __init__(
        self,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
    ):
        self.encryption_gateway = encryption_gateway
        self.vault_session_gateway = vault_session_gateway

    def execute(self, command: DecryptCommand) -> str:
        decryption_key = self.vault_session_gateway.get_decrypted_key()
        return self.encryption_gateway.decrypt(command.encrypted_data, decryption_key)
