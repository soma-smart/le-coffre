from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedShareLink:
    share_index: int
    sealed_share: str
