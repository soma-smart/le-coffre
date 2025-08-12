from typing import Optional

from vault_management_context.domain.entities import Vault, Share
from vault_management_context.domain.value_objects import VaultConfiguration
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
)
from vault_management_context.domain.services import (
    VaultCreationService,
)


class CreateVaultUseCase:
    def __init__(
        self, vault_repo: VaultRepository, shamir_gateway: ShamirGateway
    ) -> None:
        self.vault_repo = vault_repo
        self.shamir_gateway = shamir_gateway

    def execute(self, nb_shares: int, threshold: int) -> list[Share]:
        existing_vault: Optional[Vault] = self.vault_repo.get()
        configuration = VaultConfiguration.create(nb_shares, threshold)

        vault = self._create_vault(existing_vault, configuration)

        self.vault_repo.save(vault)
        return vault.shares

    def _create_vault(
        self, existing_vault: Optional[Vault], configuration: VaultConfiguration
    ) -> Vault:
        VaultCreationService.ensure_creation_allowed(existing_vault)

        shares = self.shamir_gateway.split_secret(configuration)

        return VaultCreationService.create_vault_entity(configuration, shares)
