from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from identity_access_management_context.application.gateways import (
    ServiceAccountEventRepository,
    ServiceAccountRepository,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.domain.events import ServiceAccountRevokedEvent
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway


@dataclass
class ServiceAccountRevocationService:
    """Revokes the service accounts of groups about to be deleted.

    A service account belongs to one group and acts for it: once the group is
    gone, nobody can see the account any more, let alone revoke it. Every path
    that deletes a group therefore revokes its accounts first, whether the group
    is deleted directly or along with its last owner.

    The account rows are kept, revoked, so that the audit trail still names them.
    """

    service_account_repository: ServiceAccountRepository
    """Service account repository."""

    service_account_event_repository: ServiceAccountEventRepository
    """Where each revocation is recorded."""

    token_credential_record_repository: TokenCredentialRecordRepository
    """Token credential record repository."""

    event_publisher: DomainEventPublisher
    """Where each revocation is published."""

    time_provider: TimeGateway
    """Time provider."""

    def revoke_for_groups(self, group_ids: Sequence[UUID], actor_principal_id: UUID) -> int:
        """Revoke the active service accounts of these groups. Returns how many were revoked.

        Already-revoked accounts are left alone: revoking them again would raise,
        and would overwrite the original revocation time.
        """
        if not group_ids:
            return 0

        accounts = self.service_account_repository.list_for_groups(group_ids)
        active_accounts = tuple(account for account in accounts if account.is_active)
        if not active_accounts:
            return 0

        now = self.time_provider.get_current_time()
        account_ids = [account.id for account in active_accounts]

        # Without their token records, revoked accounts can no longer authenticate.
        self.token_credential_record_repository.delete_by_principal_ids(account_ids)
        self.service_account_repository.revoke(account_ids, now)

        events = tuple(
            ServiceAccountRevokedEvent(
                event_id=uuid4(),
                occurred_on=now,
                actor_principal_id=actor_principal_id,
                service_account_id=account.id,
                service_account_name=account.name,
            )
            for account in active_accounts
        )
        self.service_account_event_repository.extend(events)
        for event in events:
            self.event_publisher.publish(event)

        return len(active_accounts)
