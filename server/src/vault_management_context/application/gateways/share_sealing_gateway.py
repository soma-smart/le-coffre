from typing import Protocol

from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import ShareLinkToken


class ShareSealingGateway(Protocol):
    def seal(self, share: Share, token: ShareLinkToken) -> str:
        """Encrypt a share under a key derived from the link token.

        The result must be openable by the recipient's browser from the token
        alone, and by nothing the server keeps.
        """
        ...
