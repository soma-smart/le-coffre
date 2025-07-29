from Crypto.Random import get_random_bytes
from Crypto.Protocol.SecretSharing import Shamir

from src.vault_management_context.business_logic.gateways.shamir_gateway import (
    ShamirGateway,
)


class CryptoShamirGateway(ShamirGateway):
    def split_secret(self, nb_shares: int, threshold: int) -> list[str]:
        secret = get_random_bytes(16)

        shares = Shamir.split(threshold, nb_shares, secret)
        return [share.hex() for _, share in shares]
