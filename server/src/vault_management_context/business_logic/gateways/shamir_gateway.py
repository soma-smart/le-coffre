from typing import Protocol


class ShamirGateway(Protocol):
    def split_secret(self, nb_shares: int, threshold: int) -> list[str]: ...
