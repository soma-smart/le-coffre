from uuid import UUID


class UserManagementDomainError(Exception):
    """Base exception for all user management domain errors"""

    pass


class UserNotFoundError(UserManagementDomainError):
    """Raised when attempting to get a password not existing"""

    def __init__(self, uunid_or_email: str | UUID):
        super().__init__(f"The requested user with {uunid_or_email} was not found")


class UserAlreadyExistsError(UserManagementDomainError):
    """Raised when attempting to create a user that already exists"""

    def __init__(self, username: str):
        super().__init__(f"The user with username '{username}' already exists")


class AdminAlreadyExistsError(UserManagementDomainError):
    """Raised when attempting to create an admin that already exists"""
