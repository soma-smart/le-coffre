from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)


class FakePasswordHashingGateway(PasswordHashingGateway):
    def hash(self, password: str) -> str:
        return f"hashed({password})"

    def verify(self, password: str, hashed_password: str) -> bool:
        return f"hashed({password})" == hashed_password
