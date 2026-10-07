from uuid import UUID


class AccessDeniedError(Exception):
    def __init__(self, user_id: UUID, resource_id: UUID):
        super().__init__(f"Access denied for user {user_id} on resource {resource_id}")


class EmailDeliveryError(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Failed to send email: {reason}")


class AuthenticationError(Exception):
    """Raised when a `Credential` proves no principal."""


class UnknownCredentialError(AuthenticationError):
    """Raised when no credential record holds the presented credential."""


class RejectedCredentialError(AuthenticationError):
    """Raised when a credential record holds the credential, but the credential does not match it."""


class OrphanedCredentialError(AuthenticationError):
    """Raised when the credential record matches, but its principal no longer exists."""
