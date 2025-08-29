from dataclasses import dataclass


@dataclass
class Vault:
    nb_shares: int
    threshold: int
    encrypted_key: str
