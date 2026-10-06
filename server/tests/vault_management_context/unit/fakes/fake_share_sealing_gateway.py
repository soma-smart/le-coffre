from vault_management_context.application.gateways import ShareSealingGateway
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import ShareLinkToken


class FakeShareSealingGateway(ShareSealingGateway):
    """Records what it sealed, under which token, so tests can check the pairing."""

    def __init__(self):
        self.sealed: list[tuple[Share, ShareLinkToken]] = []

    def seal(self, share: Share, token: ShareLinkToken) -> str:
        self.sealed.append((share, token))
        return f"sealed[{share.secret}]by[{token.lookup_hash()}]"
