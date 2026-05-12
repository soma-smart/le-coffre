from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)


class FakePasswordHashingGateway(PasswordHashingGateway):
    def __init__(self) -> None:
        self.verify_calls: list[tuple[str, bytes]] = []

    def hash(self, password: str) -> bytes:
        return f"hashed({password})".encode()

    def verify(self, password: str, hashed_password: bytes) -> bool:
        self.verify_calls.append((password, hashed_password))
        return f"hashed({password})".encode() == hashed_password
