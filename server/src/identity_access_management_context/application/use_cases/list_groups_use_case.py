from identity_access_management_context.application.gateways import GroupRepository
from identity_access_management_context.domain.entities import Group


class ListGroupsUseCase:
    def __init__(self, group_repository: GroupRepository):
        self.group_repository = group_repository

    def execute(self, include_personal: bool = True) -> list[Group]:
        """List all groups, optionally filtering out personal groups.

        Args:
            include_personal: If True, include personal groups in results. If False, only shared groups.

        Returns:
            List of groups based on filter criteria.
        """
        all_groups = self.group_repository.get_all()

        if include_personal:
            return all_groups

        return [group for group in all_groups if not group.is_personal]
