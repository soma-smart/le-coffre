from typing import Protocol


class PasswordHashingGateway(Protocol):
    def hash(self, password: str) -> bytes:
        """Hash a plain text password securely"""
        ...

    def verify(self, password: str, hashed_password: bytes) -> bool:
        """Verify a password against its hash"""
        ...
