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
