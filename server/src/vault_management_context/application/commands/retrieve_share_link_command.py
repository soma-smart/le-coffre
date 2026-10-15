from dataclasses import dataclass


@dataclass
class RetrieveShareLinkCommand:
    lookup_hash: str
