from uuid import UUID

from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.gateways import (
    UserRepository,
    UserPasswordRepository,
    GroupRepository,
    GroupMemberRepository,
    PasswordHashingGateway,
)
from identity_access_management_context.application.services import UserCreationService
from identity_access_management_context.domain.entities import User, UserPassword


class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        user_password_repository: UserPasswordRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        password_hashing_gateway: PasswordHashingGateway,
    ):
        self.user_repository = user_repository
        self.user_password_repository = user_password_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self.password_hashing_gateway = password_hashing_gateway

    def execute(self, command: CreateUserCommand) -> UUID:
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

        return user.id
