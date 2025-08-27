from uuid import UUID

from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.gateways import UserRepository
from user_management_context.domain.entities import User

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class HashingService:
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)


class CreateUserUseCase:
    def __init__(
            self,
            user_repository: UserRepository,
            hash_password_service: HashingService):
        self.user_repository = user_repository
        self.hash_password_service = hash_password_service

    def execute(self, command: CreateUserCommand) -> UUID:
        password_hashed = self.hash_password_service.hash_password(
            command.password
        )

        user = User(
            id=command.id,
            username=command.username,
            email=command.email,
            password_hashed=password_hashed,
        )

        self.user_repository.save(user)

        return user.id
