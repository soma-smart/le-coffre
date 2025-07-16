from Crypto.Random import get_random_bytes
from Crypto.Protocol.SecretSharing import Shamir

from typing import List


class ShamirSecretService:
    def split_secret(self, threshold: int, num_shares: int) -> List[str]:
        secret = get_random_bytes(16)

        shares = Shamir.split(threshold, num_shares, secret)
        return [share.hex() for _, share in shares]
