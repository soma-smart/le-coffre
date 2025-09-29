from uuid import UUID

from shared_kernel.access_control import AccessController, AccessResult, Granted


class FakeAccessController(AccessController):
    def __init__(self):
        self.access_permissions = {}
        self.owned_resources = {}

    def check_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        if self.is_owner(user_id, resource_id):
            return AccessResult(granted=Granted.ACCESS, is_owner=True)
        general_key = f"{user_id}:{resource_id}"
        if general_key in self.access_permissions:
            return AccessResult(granted=Granted.ACCESS)

        return AccessResult(granted=Granted.NOT_FOUND)

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.access_permissions[f"{user_id}:{resource_id}"] = True

    def add_access_permission(self, user_id: UUID, resource_id: UUID) -> None:
        self.access_permissions[f"{user_id}:{resource_id}"] = True

    def check_update_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has update access to resource"""
        if self.is_owner(user_id, resource_id):
            return AccessResult(granted=Granted.ACCESS, is_owner=True)
        # Check specific update permission first
        update_key = f"{user_id}:{resource_id}:update"
        if update_key in self.access_permissions:
            return AccessResult(granted=Granted.ACCESS)

        # Fallback to general access permission
        general_key = f"{user_id}:{resource_id}"
        if general_key in self.access_permissions:
            return AccessResult(granted=Granted.VIEW_ONLY)

        return AccessResult(granted=Granted.NOT_FOUND)

    def grant_update_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant update access to a resource for a specific user"""
        self.access_permissions[f"{user_id}:{resource_id}:update"] = True

    def check_delete_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has delete access to resource"""
        if self.is_owner(user_id, resource_id):
            return AccessResult(granted=Granted.ACCESS, is_owner=True)
        delete_key = f"{user_id}:{resource_id}:delete"
        if delete_key in self.access_permissions:
            return AccessResult(granted=Granted.ACCESS)
        general_key = f"{user_id}:{resource_id}"
        if general_key in self.access_permissions:
            return AccessResult(granted=Granted.VIEW_ONLY)
        return AccessResult(granted=Granted.NOT_FOUND)

    def grant_delete_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant delete access to a resource for a specific user"""
        self.access_permissions[f"{user_id}:{resource_id}:delete"] = True

    def set_owner(self, user_id: UUID, resource_id: UUID) -> None:
        """Set the owner of a resource"""
        if user_id not in self.owned_resources:
            self.owned_resources[user_id] = set()
        self.owned_resources[user_id].add(resource_id)

    def is_owner(self, user_id: UUID, resource_id: UUID) -> bool:
        """Check if the user is the owner of the resource"""
        return (
            user_id in self.owned_resources
            and resource_id in self.owned_resources[user_id]
        )
