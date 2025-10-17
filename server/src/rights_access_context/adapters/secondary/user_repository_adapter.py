from uuid import UUID
from rights_access_context.application.gateways import UserManagementGateway
from user_management_context.application.interfaces import UserRepository


class UserRepositoryAdapter(UserManagementGateway):
    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository

    def user_exists(self, user_id: UUID) -> bool:
        return self._user_repository.get_by_id(user_id) is not None
