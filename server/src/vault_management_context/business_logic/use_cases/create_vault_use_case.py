from typing import Optional

from src.vault_management_context.business_logic.models.value_objects.vault import (
    Vault,
)
from src.vault_management_context.business_logic.gateways.vault_repository import (
    VaultRepository,
)
from src.vault_management_context.business_logic.gateways.shamir_gateway import (
    ShamirGateway,
)
from src.vault_management_context.business_logic.models.domain_services.vault_domain_service import (
    VaultDomainService,
)


class CreateVaultUseCase:
    def __init__(
        self, vault_repo: VaultRepository, shamir_gateway: ShamirGateway
    ) -> None:
        self.vault_repo = vault_repo
        self.shamir_gateway = shamir_gateway

    def execute(self, nb_shares: int, threshold: int) -> Vault:
        existing_vault: Optional[Vault] = self.vault_repo.get()

        vault = self.__create_vault(existing_vault, nb_shares, threshold)

        self.vault_repo.save(vault)

        return vault

    def __create_vault(
        self, existing_vault: Optional[Vault], nb_shares: int, threshold: int
    ) -> Vault:
        VaultDomainService.pre_check(existing_vault)

        shares = self.shamir_gateway.split_secret(nb_shares, threshold)
        return VaultDomainService.create_vault(nb_shares, threshold, shares)
