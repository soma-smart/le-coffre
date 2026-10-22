from dataclasses import dataclass


@dataclass
class AcknowledgeShareLinkCommand:
    lookup_hash: str
    ack_key: str
