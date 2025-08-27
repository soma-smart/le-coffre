from user_management_context.application.use_cases.create_user_use_case import HashingService


class FakeHashPasswordService(HashingService):

    def hash_password(self, password: str) -> str:
        return f"hashed({password})"
