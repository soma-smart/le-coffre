from src.domain.password_service import PasswordService


class GeneratePasswordUseCase:
    def execute(self, length: int) -> str:
        return PasswordService().generate_password(length)
