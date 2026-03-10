from dataclasses import dataclass

from vault_management_context.domain.entities.share import Share


@dataclass
class VaultSetupResponse:
    setup_id: str
    shares: list[Share]
