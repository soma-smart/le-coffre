from vault_management_context.application.responses.vault_status import VaultStatus
from vault_management_context.domain.entities import Vault
from vault_management_context.domain.exceptions import VaultAlreadyExistsError
from vault_management_context.domain.value_objects import VaultConfiguration


class VaultCreationService:
    @staticmethod
    def ensure_creation_allowed(existing_vault: Vault | None) -> None:
        """Validate that vault creation is allowed according to business rules

        Args:
            existing_vault: Any existing vault to check against

        Raises:
            VaultAlreadyExistsError: If a vault already exists and is not in pending status
        """
        if existing_vault is not None and existing_vault.status not in (VaultStatus.PENDING.value,):
            raise VaultAlreadyExistsError()

    @staticmethod
    def create_vault_entity(configuration: VaultConfiguration, encrypted_key: str, setup_id: str) -> Vault:
        """Create a vault entity with the given configuration and encrypted key

        Args:
            configuration: The validated vault configuration
            encrypted_key: The encrypted vault key
            setup_id: The unique setup identifier

        Returns:
            The created vault entity in PENDING status
        """
        return Vault(
            nb_shares=configuration.share_count,
            threshold=configuration.threshold,
            encrypted_key=encrypted_key,
            setup_id=setup_id,
            status=VaultStatus.PENDING.value,
        )
