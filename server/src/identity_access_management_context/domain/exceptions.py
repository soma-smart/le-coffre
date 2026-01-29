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


# Legacy aliases for backward compatibility during migration
UserNotFoundError = UserNotFoundException
UserAlreadyExistsError = UserAlreadyExistsException
AdminAlreadyExistsError = AdminAlreadyExistsException
