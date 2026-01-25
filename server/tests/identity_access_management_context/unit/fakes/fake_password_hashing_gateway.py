from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)


class FakePasswordHashingGateway(PasswordHashingGateway):
    def hash(self, password: str) -> bytes:
        return f"hashed({password})".encode()

    def verify(self, password: str, hashed_password: bytes) -> bool:
        return f"hashed({password})".encode() == hashed_password
