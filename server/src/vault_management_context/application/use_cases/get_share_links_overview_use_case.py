from datetime import datetime

from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker
from vault_management_context.application.commands import GetShareLinksOverviewCommand
from vault_management_context.application.gateways import ShareLinkRepository, VaultEventRepository, VaultRepository
from vault_management_context.application.responses import ShareLinkOverview, ShareLinksOverview
from vault_management_context.domain.entities import SHARE_LINK_LIFETIME, ShareLink
from vault_management_context.domain.exceptions import VaultNotSetupException
from vault_management_context.domain.value_objects import ShareLinkStatus, StoredVaultEvent

CREATED = "VaultCreatedEvent"
RETRIEVED = "VaultShareLinkRetrievedEvent"
ACKNOWLEDGED = "VaultShareLinkAcknowledgedEvent"


class GetShareLinksOverviewUseCase(TracedUseCase):
    """Where each share link of the current setup stands. Administrators only, read-only.

    The link table alone cannot tell: a row is deleted once acknowledged and
    purged once expired, so what is gone is read from the audit events. Events
    of an earlier, abandoned setup stay in the audit trail and are ignored.
    Nothing is written and no event is emitted: looking must leave no trace in
    the very trail the view is built from.
    """

    def __init__(
        self,
        vault_repository: VaultRepository,
        share_link_repository: ShareLinkRepository,
        vault_event_repository: VaultEventRepository,
        time_gateway: TimeGateway,
    ) -> None:
        self._vault_repository = vault_repository
        self._share_link_repository = share_link_repository
        self._vault_event_repository = vault_event_repository
        self._time_gateway = time_gateway

    def execute(self, command: GetShareLinksOverviewCommand) -> ShareLinksOverview:
        AdminPermissionChecker().ensure_admin(command.requesting_user, "view the share links")

        vault = self._vault_repository.get()
        if vault is None:
            raise VaultNotSetupException()
        now = self._time_gateway.get_current_time()

        links = {link.share_index: link for link in self._share_link_repository.list_by_setup(vault.setup_id)}
        events = [
            event
            for event in self._vault_event_repository.list_events([CREATED, RETRIEVED, ACKNOWLEDGED])
            if event.event_data.get("setup_id") == vault.setup_id
        ]
        created_at = max((e.occurred_on for e in events if e.event_type == CREATED), default=None)

        overviews = [
            self._overview(index, links.get(index), events, created_at, now) for index in range(1, vault.nb_shares + 1)
        ]
        counts = {status: 0 for status in ShareLinkStatus}
        for overview in overviews:
            counts[overview.status] += 1

        return ShareLinksOverview(
            setup_id=vault.setup_id,
            nb_shares=vault.nb_shares,
            threshold=vault.threshold,
            created_at=created_at,
            links=overviews,
            counts=counts,
        )

    @staticmethod
    def _overview(
        share_index: int,
        link: ShareLink | None,
        events: list[StoredVaultEvent],
        created_at: datetime | None,
        now: datetime,
    ) -> ShareLinkOverview:
        of_link = [e for e in events if e.event_data.get("share_index") == share_index]
        openings = sorted(e.occurred_on for e in of_link if e.event_type == RETRIEVED)
        acknowledged_at = min((e.occurred_on for e in of_link if e.event_type == ACKNOWLEDGED), default=None)

        opened = bool(openings) or (link is not None and link.is_delivered())
        if acknowledged_at is not None:
            status = ShareLinkStatus.ACKNOWLEDGED
        elif opened:
            can_still_open = link is not None and link.can_be_delivered(now)
            status = ShareLinkStatus.OPENED if can_still_open else ShareLinkStatus.OPENED_UNCONFIRMED
        elif link is not None and not link.is_expired(now):
            status = ShareLinkStatus.PENDING
        else:
            status = ShareLinkStatus.EXPIRED

        expires_at = link.expires_at if link else (created_at + SHARE_LINK_LIFETIME if created_at else None)
        first_opened_at = link.delivered_at if link and link.delivered_at else (openings[0] if openings else None)
        return ShareLinkOverview(
            share_index=share_index,
            status=status,
            expires_at=expires_at,
            first_opened_at=first_opened_at,
            reopenable_until=link.reopenable_until if link else None,
            acknowledged_at=acknowledged_at,
            open_count=len(openings),
        )
