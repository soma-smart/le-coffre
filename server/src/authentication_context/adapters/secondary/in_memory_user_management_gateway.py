from uuid import UUID

from authentication_context.application.gateways import UserManagementGateway


class InMemoryUserManagementGateway(UserManagementGateway):
    def __init__(self):
        self._admin_exists = False

    async def create_admin(self, user_id: UUID, email: str, display_name: str) -> None:
        self._admin_exists = True

    async def can_create_admin(self) -> bool:
        return not self._admin_exists
