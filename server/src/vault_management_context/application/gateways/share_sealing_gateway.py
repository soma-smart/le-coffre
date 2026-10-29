from typing import Protocol

from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import ShareLinkToken


class ShareSealingGateway(Protocol):
    def seal(self, share: Share, token: ShareLinkToken, setup_id: str, share_index: int) -> str:
        """Encrypt a share under a key derived from the link token.

        The result must be openable by the recipient's browser from the token
        alone, and by nothing the server keeps. The setup id and share index are
        authenticated with it: the browser checks the ones it is handed with the
        sealed share against them.
        """
        ...

    def ack_hash(self, token: ShareLinkToken) -> str:
        """Hash of the acknowledgement key the browser derives from the token.

        Stored to check the custodian's acknowledgement later: the key itself
        is only ever computed by the token holder.
        """
        ...
