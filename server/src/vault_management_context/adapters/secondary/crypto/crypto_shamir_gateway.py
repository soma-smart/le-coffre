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

        # Embed index in the share secret: format is "index:hexsecret"
        return ShamirResult(
            [Share(f"{share[0]}:{share[1].hex()}") for share in shares], secret.hex()
        )

    def reconstruct_secret(self, shares: List[Share]) -> str:
        try:
            # Extract index from the embedded format "index:hexsecret"
            crypto_shares = []
            for share in shares:
                index_str, hex_secret = share.secret.split(":", 1)
                index = int(index_str)
                crypto_shares.append((index, bytes.fromhex(hex_secret)))

            secret_bytes = Shamir.combine(crypto_shares, False)
            return secret_bytes.hex()
        except Exception:
            # Do not propagate the original exception — it may contain share data
            # (e.g. hex decoding errors that echo the share value).
            raise ValueError("Failed to reconstruct secret") from None
