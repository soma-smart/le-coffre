from typing import Protocol


class PasswordHashingGateway(Protocol):
    def hash(self, password: str) -> str:
        """Hash a plain text password securely"""
        ...

    def verify(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        ...
