from uuid import UUID
from typing import Optional
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import UserNotFoundError


class GetUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(
        self, user_id: Optional[UUID] = None, user_email: Optional[str] = None
    ) -> User:
        if user_id is not None:
            ret = self.user_repository.get_by_id(user_id)
            if ret:
                return ret
            raise UserNotFoundError(user_id)

        if user_email is not None:
            ret = self.user_repository.get_by_email(user_email)
            if ret:
                return ret
            raise UserNotFoundError(user_email)

        raise ValueError("Either user_id or user_email must be provided.")
