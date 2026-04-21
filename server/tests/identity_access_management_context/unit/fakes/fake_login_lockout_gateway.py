from identity_access_management_context.application.gateways import (
    LoginLockoutGateway,
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class FakeLoginLockoutGateway(LoginLockoutGateway):
    """In-memory fake for unit tests of use cases that depend on login-lockout.

    Exposes call-log attributes for assertions and a ``force_lock`` helper to
    precondition a test scenario without needing to drive the gateway through
    repeated ``record_failed_login`` calls.
    """

    def __init__(self) -> None:
        self.failed_login_calls: list[str] = []
        self.successful_login_calls: list[str] = []
        self._locks: dict[str, int] = {}

    def is_locked(self, email: str) -> int | None:
        return self._locks.get(_normalize_email(email))

    def record_failed_login(self, email: str) -> None:
        self.failed_login_calls.append(_normalize_email(email))

    def record_successful_login(self, email: str) -> None:
        self.successful_login_calls.append(_normalize_email(email))
        self._locks.pop(_normalize_email(email), None)

    # ── Test-only helpers ──────────────────────────────────────────

    def force_lock(self, email: str, retry_after: int) -> None:
        """Precondition a lockout so a test can assert is_locked-gated code paths."""
        self._locks[_normalize_email(email)] = retry_after

    def release(self, email: str) -> None:
        """Force-clear any active lockout for this email."""
        self._locks.pop(_normalize_email(email), None)
