from uuid import UUID, uuid4

from identity_access_management_context.application.gateways import UserManagementGateway
from identity_access_management_context.application.use_cases import (
    CreateUserUseCase,
    CanCreateAdminUseCase,
)
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.domain.exceptions import UserAlreadyExistsError


class UserManagementGatewayAdapter(UserManagementGateway):
    """
    Adapter that calls the user management context's use cases directly via DI.
    This maintains proper separation between contexts without HTTP overhead.
    """

    def __init__(
        self,
        create_user_usecase: CreateUserUseCase,
        can_create_admin_usecase: CanCreateAdminUseCase,
    ):
        self._create_user_usecase = create_user_usecase
        self._can_create_admin_usecase = can_create_admin_usecase

    async def create_admin(self, user_id: UUID, email: str, display_name: str) -> None:
        """Create an admin user in the user management context"""
        try:
            command = CreateUserCommand(
                id=user_id,
                username=email.split("@")[0],  # Use email prefix as username
                email=email,
                name=display_name,
            )
            self._create_user_usecase.execute(command)
        except UserAlreadyExistsError:
            # User already exists, that's fine
            pass

    async def can_create_admin(self) -> bool:
        """Check if an admin can be created by querying the database"""
        response = self._can_create_admin_usecase.execute()
        return response.can_create

    async def create_user(self, user_id: UUID, email: str, display_name: str) -> None:
        """Create a regular user in the user management context"""
        try:
            command = CreateUserCommand(
                id=user_id,
                username=email.split("@")[0],  # Use email prefix as username
                email=email,
                name=display_name,
            )
            self._create_user_usecase.execute(command)
        except UserAlreadyExistsError:
            # User already exists, that's fine for SSO users
            pass
