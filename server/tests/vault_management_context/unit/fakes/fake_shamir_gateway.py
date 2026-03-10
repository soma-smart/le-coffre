from typing import List

from vault_management_context.application.gateways import (
    ShamirGateway,
)
from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.value_objects import (
    ShamirResult,
    VaultConfiguration,
)


class FakeShamirGateway(ShamirGateway):
    def __init__(self):
        self._shamir_result: ShamirResult | None = None

    def set_shamir_result(self, result: ShamirResult) -> None:
        self._shamir_result = result

    def create_shares(self, configuration: VaultConfiguration) -> ShamirResult:
        if self._shamir_result is None:
            raise ValueError("No shamir result configured")
        return self._shamir_result

    def reconstruct_secret(self, shares: List[Share]) -> str:
        if self._shamir_result is None or shares != self._shamir_result.shares:
            raise ValueError("Reconstruction failed")

        return self._shamir_result.master_key
