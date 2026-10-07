from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.gateways import ShareLinkRepository


class PurgeExpiredShareLinksUseCase(TracedUseCase):
    """Delete the share links that can no longer be retrieved.

    Two kinds: links past their 48-hour lifetime, and links opened but never
    acknowledged whose reopen window has ended (ShareLink.is_purgeable). Either
    way the sealed share has no reason to stay in the database. Run on a timer
    rather than on retrieval, so the rows go even if nobody ever tries a link
    again.
    """

    def __init__(self, share_link_repository: ShareLinkRepository, time_gateway: TimeGateway) -> None:
        self._share_link_repository = share_link_repository
        self._time_gateway = time_gateway

    def execute(self) -> None:
        self._share_link_repository.purge_expired(self._time_gateway.get_current_time())
