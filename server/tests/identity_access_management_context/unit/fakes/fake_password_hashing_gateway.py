from identity_access_management_context.application.gateways import (
    PasswordHashingGateway,
)


class FakePasswordHashingGateway(PasswordHashingGateway):
    def __init__(self) -> None:
        self._verification_count = 0
        self._last_verified_password: str | None = None
        self._last_verified_hash: bytes | None = None

    def hash(self, password: str) -> bytes:
        return f"hashed({password})".encode()

    def verify(self, password: str, hashed_password: bytes) -> bool:
        self._verification_count += 1
        self._last_verified_password = password
        self._last_verified_hash = hashed_password
        return f"hashed({password})".encode() == hashed_password

    def get_verification_count(self) -> int:
        """Return the number of times verify() was called."""
        return self._verification_count

    def get_last_verified_password(self) -> str | None:
        """Return the last password passed to verify()."""
        return self._last_verified_password

    def get_last_verified_hash(self) -> bytes | None:
        """Return the last hash passed to verify()."""
        return self._last_verified_hash
