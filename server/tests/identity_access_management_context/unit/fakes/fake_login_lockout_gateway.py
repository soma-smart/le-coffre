from identity_access_management_context.application.gateways import (
    LoginLockoutGateway,
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class FakeLoginLockoutGateway(LoginLockoutGateway):
    """In-memory fake for unit-testing use cases that depend on login lockout.

    Tests precondition a lockout with :meth:`force_lock` rather than driving the
    gateway through repeated failures; call logs let tests assert which branch of
    the use case fired.
    """

    def __init__(self) -> None:
        self.failed_login_calls: list[str] = []
        self.successful_login_calls: list[str] = []
        self._locks: dict[str, int] = {}

    def is_locked(self, email: str) -> int | None:
        retry_after = self._locks.get(_normalize_email(email))
        if retry_after is None or retry_after <= 0:
            return None
        return retry_after

    def record_failed_login(self, email: str) -> None:
        self.failed_login_calls.append(_normalize_email(email))

    def record_successful_login(self, email: str) -> None:
        key = _normalize_email(email)
        self.successful_login_calls.append(key)
        self._locks.pop(key, None)

    # ── Test-only helpers ──────────────────────────────────────────

    def force_lock(self, email: str, retry_after: int) -> None:
        """Precondition a lockout; pass ``retry_after=0`` to seed an expired entry."""
        self._locks[_normalize_email(email)] = retry_after

    def release(self, email: str) -> None:
        self._locks.pop(_normalize_email(email), None)
