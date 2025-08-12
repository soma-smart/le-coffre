from dataclasses import dataclass

from .share import Share


@dataclass
class Vault:
    nb_shares: int
    threshold: int
    shares: list[Share]
