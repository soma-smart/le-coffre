from Crypto.Random import get_random_bytes
from Crypto.Protocol.SecretSharing import Shamir
from typing import List

from vault_management_context.domain.entities.share import Share
from vault_management_context.domain.value_objects import (
    VaultConfiguration,
    ShamirResult,
)
from vault_management_context.application.gateways import (
    ShamirGateway,
)


class CryptoShamirGateway(ShamirGateway):
    def create_shares(self, configuration: VaultConfiguration) -> ShamirResult:
        secret = get_random_bytes(16)

        shares = Shamir.split(
            configuration.threshold,
            configuration.share_count,
            secret,
            False,
        )

        return ShamirResult(
            [Share(share[0], share[1].hex()) for share in shares], secret.hex()
        )

    def reconstruct_secret(self, shares: List[Share]) -> str:
        try:
            crypto_shares = [
                (share.index, bytes.fromhex(share.secret)) for share in shares
            ]
            secret_bytes = Shamir.combine(crypto_shares, False)
            return secret_bytes.hex()
        except Exception as e:
            raise ValueError(f"Failed to reconstruct secret: {e}") from e
