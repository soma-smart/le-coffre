from src.vault_management_context.application.gateways import VaultRepository


class GetVaultStatusUseCase:
    def __init__(self, vault_repository: VaultRepository):
        self.vault_repository = vault_repository

    def execute(self) -> bool:
        return self.vault_repository.get() is not None
