from typing import List, Optional

from vault_management_context.domain.entities import Vault, Share
from vault_management_context.domain.value_objects import VaultConfiguration
from vault_management_context.domain.exceptions import VaultAlreadyExistsError


class VaultCreationService:
    @staticmethod
    def pre_check(existing_vault: Optional[Vault]):
        if existing_vault is not None:
            raise VaultAlreadyExistsError()

    @staticmethod
    def create_vault(configuration: VaultConfiguration, shares: List[Share]) -> Vault:
        return Vault(
            nb_shares=configuration.share_count.value,
            threshold=configuration.threshold.value,
            shares=shares,
        )
