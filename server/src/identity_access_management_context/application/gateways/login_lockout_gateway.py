from typing import Protocol


class LoginLockoutGateway(Protocol):
    def is_locked(self, email: str) -> int | None:
        """Return the remaining lockout duration in seconds if the account is locked, else None."""
        ...

    def record_failed_login(self, email: str) -> None:
        """Record a failed login attempt for this email; triggers a lockout when the threshold is reached."""
        ...

    def record_successful_login(self, email: str) -> None:
        """Clear all failure / lockout state for this email."""
        ...
