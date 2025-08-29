from uuid import UUID


class UserManagementDomainError(Exception):
    """Base exception for all user management domain errors"""
    pass


class UserNotFoundError(UserManagementDomainError):
    """Raised when attempting to get a password not existing"""

    def __init__(self, uuid: UUID):
        super().__init__(f"The requested user with ID {uuid} was not found")
