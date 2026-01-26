"""Domain service for password access control logic"""

from typing import Optional
from uuid import UUID

from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.domain.value_objects import PasswordPermission


class PasswordAccessService:
    """Domain service to encapsulate access control logic"""

    def __init__(
        self,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
    ):
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway

    def get_user_access_group(self, user_id: UUID, password_id: UUID) -> Optional[UUID]:
        """
        Get the group ID through which user has access to the password.
        Returns None if user has no access.
        """
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user is owner or member of this group
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                # If the group is the owner or has READ permission, user has access
                if is_owner or PasswordPermission.READ in permissions:
                    return group_id

        return None

    def user_has_access(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        return self.get_user_access_group(user_id, password_id) is not None

    def user_has_access_through_groups(
        self, user_id: UUID, password_id: UUID
    ) -> Optional[tuple[UUID, UUID]]:
        """
        Check if user has access to password through groups.
        Returns (user_group_id, owner_group_id) if access granted, None otherwise.
        """
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                if is_owner:
                    # User's group is the owner
                    return (group_id, group_id)
                elif PasswordPermission.READ in permissions:
                    # User's group has READ permission, need to find owner
                    for owner_group_id, (is_owner_group, _) in all_permissions.items():
                        if is_owner_group:
                            return (group_id, owner_group_id)

        return None
