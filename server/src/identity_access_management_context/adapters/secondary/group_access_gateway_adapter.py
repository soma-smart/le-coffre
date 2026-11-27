from uuid import UUID

from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
    ServiceAccountRepository,
)
from identity_access_management_context.domain.entities import ServiceAccount


class GroupAccessGatewayAdapter:
    """Adapter implementing the GroupAccessGateway interface from Password Management context.

    This adapter allows the Password Management context to verify group ownership
    without creating a direct dependency on the IAM context.
    """

    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        service_account_repository: ServiceAccountRepository,
    ):
        self._group_repository = group_repository
        self._group_member_repository = group_member_repository
        self._service_account_repository = service_account_repository
        # Built per request, and a listing asks about one principal for many groups.
        self._service_accounts: dict[UUID, ServiceAccount | None] = {}

    def _service_account(self, principal_id: UUID) -> ServiceAccount | None:
        if principal_id not in self._service_accounts:
            (self._service_accounts[principal_id],) = self._service_account_repository.get_by_ids([principal_id])
        return self._service_accounts[principal_id]

    def is_principal_owner_of_group(self, principal_id: UUID, group_id: UUID) -> bool:
        """Check if a user is the owner of a group.

        Args:
            principal_id: The ID of the user to check
            group_id: The ID of the group to check

        Returns:
            True if the user owns the group, False otherwise
        """
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return False

        # For personal groups, check if the principal_id matches
        if group.is_personal and group.principal_id == principal_id:
            return True

        # For shared groups, check membership
        return self._group_member_repository.is_owner(group_id, principal_id)

    def is_principal_member_of_group(self, principal_id: UUID, group_id: UUID) -> bool:
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return False

        # For personal groups, check if the principal_id matches
        if group.is_personal and group.principal_id == principal_id:
            return True

        # For shared groups, check membership
        if self._group_member_repository.is_member(group_id, principal_id):
            return True

        # A service account belongs to the one group it was created in, as a member:
        # it reads what the group reads, and is never an owner, so it can change nothing.
        service_account = self._service_account(principal_id)
        return service_account is not None and service_account.is_active and service_account.group_id == group_id

    def group_exists(self, group_id: UUID) -> bool:
        """Check if a group exists.

        Args:
            group_id: The ID of the group to check

        Returns:
            True if the group exists, False otherwise
        """
        return self._group_repository.get_by_id(group_id) is not None

    def get_group_owner_principals(self, group_id: UUID) -> list[UUID]:
        """Get all users who own this group.

        Args:
            group_id: The ID of the group

        Returns:
            List of user IDs who own this group
        """
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return []

        # For personal groups, return the principal_id
        if group.is_personal and group.principal_id:
            return [group.principal_id]

        # For shared groups, get all owner members
        members = self._group_member_repository.get_members(group_id)
        return [member.principal_id for member in members if member.is_owner]

    def get_group_member_principals(self, group_id: UUID) -> list[UUID]:
        """Get the users who belong to this group as members (not owners).

        Args:
            group_id: The ID of the group

        Returns:
            List of user IDs who are non-owner members of this group
        """
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return []

        # Personal groups have a single owner and no separate members.
        if group.is_personal:
            return []

        members = self._group_member_repository.get_members(group_id)
        return [member.principal_id for member in members if not member.is_owner]
