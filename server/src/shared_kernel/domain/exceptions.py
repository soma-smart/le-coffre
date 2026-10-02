from uuid import UUID


class AccessDeniedError(Exception):
    def __init__(self, user_id: UUID, resource_id: UUID):
        super().__init__(f"Access denied for user {user_id} on resource {resource_id}")


class EmailDeliveryError(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Failed to send email: {reason}")


class ReadOnlyCredentialError(Exception):
    """Raised when a read-only credential attempts a mutating request.

    Maps to 403 rather than 401: the credential is valid, it simply cannot do
    this. Telling the caller to re-authenticate would be wrong and would send a
    browser extension into a pointless re-pairing loop.
    """

    def __init__(self, method: str):
        super().__init__(f"This credential is read-only and cannot perform a {method.upper()} request")
        self.method = method


class AuthenticationError(Exception):
    """Raised when a `Credential` proves no principal."""


class UnknownCredentialError(AuthenticationError):
    """Raised when no credential record holds the presented credential."""


class RejectedCredentialError(AuthenticationError):
    """Raised when a credential record holds the credential, but the credential does not match it."""


class OrphanedCredentialError(AuthenticationError):
    """Raised when the credential record matches, but its principal no longer exists."""
