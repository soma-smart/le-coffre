"""Links issued for use case tests, with the keys a custodian's browser would derive."""

import hashlib
from datetime import datetime

from vault_management_context.domain.entities import ShareLink

SETUP_ID = "setup-1"


def lookup(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ack_key(token: str) -> str:
    """Stands in for the HKDF the browser runs: any 256 bits only the token yields."""
    return hashlib.sha256(f"ack-{token}".encode()).hexdigest()


def issue_links(share_link_repository, now: datetime, indexes=(1, 2, 3)) -> list[ShareLink]:
    issued = [
        ShareLink.create(
            setup_id=SETUP_ID,
            share_index=index,
            lookup_hash=lookup(f"token-{index}"),
            ack_hash=hashlib.sha256(bytes.fromhex(ack_key(f"token-{index}"))).hexdigest(),
            sealed_share=f"sealed-{index}",
            now=now,
        )
        for index in indexes
    ]
    share_link_repository.replace_all(issued)
    return issued
