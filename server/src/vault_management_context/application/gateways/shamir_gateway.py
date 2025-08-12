from typing import Protocol
from typing import List
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import VaultConfiguration


class ShamirGateway(Protocol):
    def split_secret(self, configuration: VaultConfiguration) -> List[Share]: ...
