from dataclasses import dataclass

from vault_management_context.domain.entities import Share


@dataclass(frozen=True)
class ShamirResult:
    shares: list[Share]
    master_key: str
