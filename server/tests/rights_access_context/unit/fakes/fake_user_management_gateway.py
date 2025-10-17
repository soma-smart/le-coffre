from uuid import UUID
from rights_access_context.application.gateways import UserManagementGateway


class FakeUserManagementGateway(UserManagementGateway):
    def __init__(self):
        self._existing_users: set[UUID] = set()

    def add_user(self, user_id: UUID) -> None:
        """Helper method for tests to add users"""
        self._existing_users.add(user_id)

    def user_exists(self, user_id: UUID) -> bool:
        return user_id in self._existing_users
