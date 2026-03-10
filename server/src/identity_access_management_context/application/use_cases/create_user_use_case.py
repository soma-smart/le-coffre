from uuid import UUID

from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
    PasswordHashingGateway,
    UserEventRepository,
    UserPasswordRepository,
    UserRepository,
)
from identity_access_management_context.application.services import UserCreationService
from identity_access_management_context.domain.entities import User, UserPassword
from identity_access_management_context.domain.events import UserCreatedEvent
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class CreateUserUseCase(TracedUseCase):
    def __init__(
        self,
        user_repository: UserRepository,
        user_password_repository: UserPasswordRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        password_hashing_gateway: PasswordHashingGateway,
        event_publisher: DomainEventPublisher,
        user_event_repository: UserEventRepository,
    ):
        self.user_repository = user_repository
        self.user_password_repository = user_password_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self.password_hashing_gateway = password_hashing_gateway
        self._event_publisher = event_publisher
        self._user_event_repository = user_event_repository

    def execute(self, command: CreateUserCommand) -> UUID:
        AdminPermissionChecker().ensure_admin(command.requesting_user, "Create User")

        user = User(
            id=command.id,
            username=command.username,
            email=command.email,
            name=command.name,
        )

        self.user_repository.save(user)

        password_hash = self.password_hashing_gateway.hash(command.password)

        user_password = UserPassword(
            id=command.id,
            email=command.email,
            password_hash=password_hash,
            display_name=command.name,
        )

        self.user_password_repository.save(user_password)

        UserCreationService.create_personal_group_and_set_ownership(
            user_id=user.id,
            username=user.username,
            group_repository=self.group_repository,
            group_member_repository=self.group_member_repository,
        )

        event = UserCreatedEvent(
            user_id=user.id,
            username=user.username,
            email=user.email,
            created_by_user_id=command.requesting_user.user_id,
        )
        self._event_publisher.publish(event)
        self._user_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requesting_user.user_id,
            event_data={"user_id": str(user.id), "username": user.username, "email": user.email},
        )

        return user.id
