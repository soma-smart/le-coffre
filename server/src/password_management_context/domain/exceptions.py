from uuid import UUID


class PasswordManagementDomainError(Exception):
    """Base exception for all password management domain errors"""

    pass


class PasswordNotFoundError(PasswordManagementDomainError):
    """Raised when attempting to get a password not existing"""

    def __init__(self, uuid: UUID):
        super().__init__(f"The requested password with ID {uuid} was not found")


class FolderNotFoundError(PasswordManagementDomainError):
    """Raised when attempting to list passwords from a non-existing folder"""

    def __init__(self, folder_name: str):
        super().__init__(f"The requested folder '{folder_name}' was not found")
