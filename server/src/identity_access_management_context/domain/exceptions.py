from uuid import UUID


class IdentityAccessManagementDomainError(Exception):
    """Base exception for all identity and access management domain errors"""

    pass


# Authentication-related exceptions
class AuthenticationDomainError(IdentityAccessManagementDomainError):
    """Base exception for authentication errors"""

    pass


class InvalidCredentialsException(AuthenticationDomainError):
    pass


class InvalidSessionException(AuthenticationDomainError):
    pass


class InvalidTokenException(InvalidSessionException):
    pass


class SessionNotFoundException(InvalidSessionException):
    pass


class InsufficientRoleException(InvalidSessionException):
    pass


class InvalidSsoCodeException(AuthenticationDomainError):
    pass


class InvalidSsoSettingsException(AuthenticationDomainError):
    pass


class DisallowedSsoEndpointException(InvalidSsoSettingsException):
    """Raised when an SSO URL targets a disallowed scheme or a private/internal address."""

    def __init__(self, message: str = "The provided SSO URL is not allowed") -> None:
        super().__init__(message)


class InvalidRefreshTokenException(AuthenticationDomainError):
    pass


class PasswordPolicyViolationError(IdentityAccessManagementDomainError):
    """Base exception for account-password policy violations.

    Deliberately NOT an ``AuthenticationDomainError``: that family maps to 401 on
    some routes, whereas a rejected new password is a bad request (400).
    """

    pass


class PasswordTooShortError(PasswordPolicyViolationError):
    """Raised when an account password is shorter than the policy minimum."""

    def __init__(self, current_length: int, min_length: int):
        super().__init__(
            f"Password is too short: {current_length} characters. Minimum required: {min_length} characters"
        )
        self.current_length = current_length
        self.min_length = min_length


class CommonPasswordError(PasswordPolicyViolationError):
    """Raised when an account password is a well-known common password."""

    def __init__(self):
        super().__init__("This password is too common. Please choose a less predictable one.")


class AccountLockedException(AuthenticationDomainError):
    """Raised when a login is attempted against an account that is temporarily locked.

    Carries ``retry_after_seconds`` as a typed attribute so the route can emit
    the ``Retry-After`` header. Domain layer stays import-pure — the caller
    (use case) bridges from the application-layer ``LockoutStatus`` value
    object, which owns the positivity invariant.
    """

    def __init__(self, retry_after_seconds: int):
        if retry_after_seconds < 1:
            raise ValueError(f"AccountLockedException.retry_after_seconds must be >= 1; got {retry_after_seconds}")
        super().__init__(f"Account temporarily locked. Retry after {retry_after_seconds}s.")
        self.retry_after_seconds = retry_after_seconds


# User-related exceptions
class UserNotFoundException(IdentityAccessManagementDomainError):
    """Raised when attempting to get a user that doesn't exist"""

    def __init__(self, uuid_or_email: str | UUID):
        super().__init__(f"The requested user with {uuid_or_email} was not found")


class UserAlreadyExistsException(IdentityAccessManagementDomainError):
    """Raised when attempting to create a user that already exists"""

    def __init__(self, username: str):
        super().__init__(f"The user with username '{username}' already exists")


class SsoUserAlreadyExistsException(IdentityAccessManagementDomainError):
    pass


class UserUpdateNotAllowedException(IdentityAccessManagementDomainError):
    """Raised when a user attempts to update a user they are neither (themselves nor an admin)"""

    def __init__(self, requesting_user_id: UUID, target_user_id: UUID):
        super().__init__(f"User '{requesting_user_id}' is not allowed to update user '{target_user_id}'")


# Group-related exceptions
class GroupAlreadyExistsException(IdentityAccessManagementDomainError):
    """Raised when attempting to create a group with a name that already exists"""

    def __init__(self, group_name: str):
        super().__init__(f"The group with name '{group_name}' already exists")


class GroupNotFoundException(IdentityAccessManagementDomainError):
    """Raised when attempting to access a group that doesn't exist"""

    def __init__(self, group_id: UUID):
        super().__init__(f"The group with ID '{group_id}' was not found")


class UserNotOwnerOfGroupException(IdentityAccessManagementDomainError):
    """Raised when a user attempts an owner-only action on a group they don't own"""

    def __init__(self, user_id: UUID, group_id: UUID):
        super().__init__(f"User '{user_id}' is not an owner of group '{group_id}'")


class CannotModifyPersonalGroupException(IdentityAccessManagementDomainError):
    """Raised when attempting to add/remove members from a personal group"""

    def __init__(self, group_id: UUID):
        super().__init__(f"Cannot modify members of personal group '{group_id}'")


class UserNotMemberOfGroupException(IdentityAccessManagementDomainError):
    """Raised when attempting to remove a user who is not a member"""

    def __init__(self, user_id: UUID, group_id: UUID):
        super().__init__(f"User '{user_id}' is not a member of group '{group_id}'")


class CannotRemoveOwnerException(IdentityAccessManagementDomainError):
    """Raised when attempting to remove an owner from a group"""

    def __init__(self, user_id: UUID, group_id: UUID):
        super().__init__(f"Cannot remove owner '{user_id}' from group '{group_id}'")


class CannotDeletePersonalGroupException(IdentityAccessManagementDomainError):
    """Raised when attempting to delete a personal group"""

    def __init__(self, group_id: UUID):
        super().__init__(f"Cannot delete personal group '{group_id}'")


class CannotDeleteGroupStillUsedException(IdentityAccessManagementDomainError):
    """Raised when attempting to delete a group that is still in use"""

    def __init__(self, group_id: UUID):
        super().__init__(f"Cannot delete group '{group_id}' because it is still in use")


# Admin-related exceptions
class AdminNotFoundException(IdentityAccessManagementDomainError):
    pass


class AdminAlreadyExistsException(IdentityAccessManagementDomainError):
    """Raised when attempting to create an admin that already exists"""

    pass


class UserAlreadyAdminException(IdentityAccessManagementDomainError):
    """Raised when attempting to promote a user who is already an admin"""

    def __init__(self, user_id: UUID):
        super().__init__(f"User '{user_id}' is already an admin")


class SsoConfigurationNotFoundError(IdentityAccessManagementDomainError):
    """Raised when SSO is not configured and an SSO operation is attempted"""

    def __init__(self):
        super().__init__("SSO is not configured")


class SsoEncryptionUnavailableError(IdentityAccessManagementDomainError):
    """Raised when the vault is locked and SSO encryption/decryption cannot be performed"""

    def __init__(self):
        super().__init__("Vault is locked: unlock the vault to perform this operation")


# Service-account-related exceptions
class ServiceAccountNotFoundException(IdentityAccessManagementDomainError):
    """Raised when no service account matches the requested id within its group"""

    def __init__(self, service_account_id: UUID):
        super().__init__(f"Service account '{service_account_id}' not found")


class ServiceAccountAlreadyExistsException(IdentityAccessManagementDomainError):
    """Raised when a group already has an active service account under that name"""

    def __init__(self, group_id: UUID, name: str):
        super().__init__(f"Group '{group_id}' already has an active service account named '{name}'")


class ServiceAccountAlreadyRevokedException(IdentityAccessManagementDomainError):
    """Raised when regenerating or revoking a service account that is already revoked"""

    def __init__(self, service_account_id: UUID):
        super().__init__(f"Service account '{service_account_id}' has already been revoked")


class TooManyActiveServiceAccountsError(IdentityAccessManagementDomainError):
    """Raised when a group already has the maximum of active service accounts"""

    def __init__(self, active_count: int, max_active: int):
        self.active_count = active_count
        self.max_active = max_active
        super().__init__(
            f"This group already has {active_count} active service accounts "
            f"(maximum {max_active}). Revoke one before creating another."
        )


class InvalidServiceAccountNameError(IdentityAccessManagementDomainError):
    """Raised when a service account name is blank or longer than the allowed maximum"""

    def __init__(self, reason: str):
        super().__init__(f"Invalid service account name: {reason}")


class InvalidServiceAccountTokenError(IdentityAccessManagementDomainError):
    """Raised when a presented token is too short to have been generated by us"""

    def __init__(self) -> None:
        super().__init__("The service account token is malformed")


# Legacy aliases for backward compatibility during migration
UserNotFoundError = UserNotFoundException
UserAlreadyExistsError = UserAlreadyExistsException
AdminAlreadyExistsError = AdminAlreadyExistsException
