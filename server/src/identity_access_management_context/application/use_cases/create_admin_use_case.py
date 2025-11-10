from uuid import UUID

from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import AdminAlreadyExistsError
from identity_access_management_context.application.services import (
    AdminExistenceService,
)
from shared_kernel.domain import ADMIN_ROLE


class CreateAdminUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: CreateUserCommand) -> UUID:
        if AdminExistenceService.admin_exists(self.user_repository):
            raise AdminAlreadyExistsError()

        admin = User(
            id=command.id,
            email=command.email,
            username=command.username,
            name=command.name,
            roles=[ADMIN_ROLE],
        )

        self.user_repository.save(admin)
        return admin.id
