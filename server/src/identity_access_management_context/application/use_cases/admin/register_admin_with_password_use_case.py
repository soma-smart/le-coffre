from uuid import UUID

from identity_access_management_context.application.commands import (
    RegisterAdminWithPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.application.services import (
    UserManagementService,
    UserCreationService,
)
from identity_access_management_context.domain.entities import UserPassword
from identity_access_management_context.domain.events import AdminRegisteredEvent
from identity_access_management_context.domain.exceptions import (
    AdminAlreadyExistsException,
)
from shared_kernel.application.gateways import DomainEventPublisher


class RegisterAdminWithPasswordUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
    ):
        self._user_password_repository = user_password_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._user_repository = user_repository
        self._group_repository = group_repository
        self._group_member_repository = group_member_repository
        self._event_publisher = event_publisher

    async def execute(self, command: RegisterAdminWithPasswordCommand) -> UUID:
        # Create service instance
        user_management_service = UserManagementService(
            self._user_repository, self._password_hashing_gateway
        )

        # Check if admin can be created
        if not user_management_service.can_create_admin():
            raise AdminAlreadyExistsException("An admin account already exists")

        # Hash password and save to password repository
        password_hash = self._password_hashing_gateway.hash(command.password)
        user_password = UserPassword(
            id=command.id,
            email=command.email,
            password_hash=password_hash,
            display_name=command.display_name,
        )
        self._user_password_repository.save(user_password)

        # Create admin user via service
        user = user_management_service.create_admin(
            user_id=command.id,
            email=command.email,
            username=command.email.split("@")[0],
            name=command.display_name,
        )

        # Create personal group for the admin user
        UserCreationService.create_personal_group_and_set_ownership(
            user_id=user.id,
            username=user.username,
            group_repository=self._group_repository,
            group_member_repository=self._group_member_repository,
        )

        self._event_publisher.publish(AdminRegisteredEvent(
            admin_id=user_password.id,
            email=command.email,
        ))

        return user_password.id
