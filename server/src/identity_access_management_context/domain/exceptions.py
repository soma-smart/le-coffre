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


class InvalidRefreshTokenException(AuthenticationDomainError):
    pass


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


# Legacy aliases for backward compatibility during migration
UserNotFoundError = UserNotFoundException
UserAlreadyExistsError = UserAlreadyExistsException
AdminAlreadyExistsError = AdminAlreadyExistsException
