from uuid import UUID

from shared_kernel.access_control import AccessController, AccessResult, Granted


class FakeAccessController(AccessController):
    def __init__(self):
        self.granted_accesses = []
        self.access_permissions = {}

    def check_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        general_key = f"{user_id}:{resource_id}"
        if general_key in self.access_permissions:
            return AccessResult(granted=Granted.ACCESS)

        return AccessResult(granted=Granted.NOT_FOUND)

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.granted_accesses.append((user_id, resource_id))
        self.access_permissions[f"{user_id}:{resource_id}"] = True

    def add_access_permission(self, user_id: UUID, resource_id: UUID) -> None:
        self.access_permissions[f"{user_id}:{resource_id}"] = True

    def check_update_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has update access to resource"""
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

    def check_create_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has create access to resource"""
        create_key = f"{user_id}:{resource_id}:create"
        if create_key in self.access_permissions:
            return AccessResult(granted=Granted.ACCESS)
        general_key = f"{user_id}:{resource_id}"
        if general_key in self.access_permissions:
            return AccessResult(granted=Granted.VIEW_ONLY)
        return AccessResult(granted=Granted.NOT_FOUND)

    def grant_create_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant create access to a resource for a specific user"""
        self.access_permissions[f"{user_id}:{resource_id}:create"] = True
