from collections.abc import Sequence
from uuid import UUID, uuid4

from identity_access_management_context.application.commands import ListServiceAccountsCommand
from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
    ServiceAccountEventRepository,
    ServiceAccountRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    ListServiceAccountsResponse,
    ServiceAccountSummaryResponse,
)
from identity_access_management_context.application.services import GroupManagementPermissionService
from identity_access_management_context.domain.events import ServiceAccountsListedEvent
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.domain.services import AdminPermissionChecker

from ._use_case import ServiceAccountUseCase


class ListServiceAccountsUseCase(
    ServiceAccountUseCase[ListServiceAccountsCommand, ServiceAccountsListedEvent, ListServiceAccountsResponse]
):
    _user_repository: UserRepository
    _group_repository: GroupRepository
    _group_member_repository: GroupMemberRepository
    _max_active_accounts: int

    def __init__(
        self,
        service_account_repository: ServiceAccountRepository,
        permission_service: GroupManagementPermissionService,
        event_publisher: DomainEventPublisher,
        service_account_event_repository: ServiceAccountEventRepository,
        time_provider: TimeGateway,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        max_active_accounts: int,
    ):
        super().__init__(
            service_account_repository,
            permission_service,
            event_publisher,
            service_account_event_repository,
            time_provider,
        )
        self._user_repository = user_repository
        self._group_repository = group_repository
        self._group_member_repository = group_member_repository
        self._max_active_accounts = max_active_accounts

    def _readable_group_ids(self, command: ListServiceAccountsCommand) -> Sequence[UUID]:
        """Return the groups this listing covers, refusing one the caller cannot manage."""
        if command.group_id is not None:
            self._permissions.ensure_user_can_manage_group(command.requesting_user, command.group_id)
            return (command.group_id,)

        # An administrator manages every group, so an unscoped listing spans them all.
        if AdminPermissionChecker.is_admin(command.requesting_user):
            return [group.id for group in self._group_repository.get_all()]

        return self._group_member_repository.get_group_ids_owned_by(command.requesting_user.user_id)

    def _execute(
        self, command: ListServiceAccountsCommand
    ) -> tuple[ServiceAccountsListedEvent, ListServiceAccountsResponse]:
        # Retrieve the service accounts
        group_ids = self._readable_group_ids(command)
        accounts = tuple(self._repository.list_for_groups(group_ids))
        facts = self._event_repository.get_creation_facts(tuple(account.id for account in accounts))

        # Get user names
        # NOTE: Repositories should handle bulk queries to avoid such loops
        display_names: dict = {}
        creator_ids = {fact.created_by_user_id for fact in facts if fact.created_by_user_id}
        for creator_id in creator_ids:
            user = self._user_repository.get_by_id(creator_id)
            display_names[creator_id] = user.name if user is not None else None

        summaries = tuple(
            ServiceAccountSummaryResponse(
                id=account.id,
                group_id=account.group_id,
                name=account.name,
                created_by_user_id=fact.created_by_user_id,
                created_by_user_name=display_names.get(fact.created_by_user_id),
                created_at=fact.created_at,
                revoked_at=account.revoked_at,
            )
            for account, fact in zip(accounts, facts, strict=True)
        )

        # Sort summaries
        dated_summaries = sorted(
            filter(lambda s: s.created_at is not None, summaries),
            key=lambda s: s.created_at,  # type: ignore
            reverse=True,
        )  # pyright: ignore[reportCallIssue]
        undated_summaries = [s for s in summaries if s.created_at is None]

        event = ServiceAccountsListedEvent(
            event_id=uuid4(),
            occurred_on=self._time_provider.get_current_time(),
            user_id=command.requesting_user.user_id,
            group_id=command.group_id,
        )
        # Counted on the accounts rather than the summaries: the account row is the
        # credential itself, while a summary depends on a creation event that may be missing.
        active = sum(1 for account in accounts if account.is_active)

        response = ListServiceAccountsResponse(
            items=tuple(dated_summaries + undated_summaries),
            active=active,
            max_active=self._max_active_accounts,
        )

        return event, response
