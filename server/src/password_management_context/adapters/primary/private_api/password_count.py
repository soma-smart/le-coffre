from password_management_context.application.gateways import PasswordRepository


class PasswordCountApi:
    def __init__(self, password_repository: PasswordRepository):
        self._password_repository = password_repository

    def count(self) -> int:
        return self._password_repository.count()
