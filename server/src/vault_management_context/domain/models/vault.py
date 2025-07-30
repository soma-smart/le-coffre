from dataclasses import dataclass


@dataclass
class Vault:
    nb_shares: int
    threshold: int
    shares: list[str]
