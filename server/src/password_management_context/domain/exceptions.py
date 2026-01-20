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


class GroupNotFoundError(PasswordManagementDomainError):
    """Raised when attempting to create a password for a non-existing group"""

    def __init__(self, group_id: UUID):
        super().__init__(f"The group with ID {group_id} was not found")


class UserNotOwnerOfGroupError(PasswordManagementDomainError):
    """Raised when a user attempts to create a password for a group they don't own"""

    def __init__(self, user_id: UUID, group_id: UUID):
        super().__init__(f"User {user_id} is not the owner of group {group_id}")


class PasswordComplexityError(PasswordManagementDomainError):
    """Base exception for password complexity violations"""

    pass


class PasswordTooShortError(PasswordComplexityError):
    """Raised when password is too short"""

    def __init__(self, current_length: int, min_length: int):
        self.current_length = current_length
        self.min_length = min_length
        super().__init__(
            f"Password is too short: {current_length} characters. "
            f"Minimum required: {min_length} characters"
        )


class PasswordMissingUppercaseError(PasswordComplexityError):
    """Raised when password doesn't contain uppercase letters"""

    def __init__(self):
        super().__init__("Password must contain at least one uppercase letter")


class PasswordMissingLowercaseError(PasswordComplexityError):
    """Raised when password doesn't contain lowercase letters"""

    def __init__(self):
        super().__init__("Password must contain at least one lowercase letter")


class PasswordMissingDigitError(PasswordComplexityError):
    """Raised when password doesn't contain digits"""

    def __init__(self):
        super().__init__("Password must contain at least one digit")


class PasswordMissingSpecialCharError(PasswordComplexityError):
    """Raised when password doesn't contain special characters"""

    def __init__(self):
        super().__init__("Password must contain at least one special character")


class PasswordContainsForbiddenPatternError(PasswordComplexityError):
    """Raised when password contains forbidden patterns"""

    def __init__(self, forbidden_pattern: str):
        self.forbidden_pattern = forbidden_pattern
        super().__init__(f"Password contains forbidden pattern: {forbidden_pattern}")


class PasswordAccessDeniedError(PasswordManagementDomainError):
    """Raised when user doesn't have permission to access a password"""

    def __init__(self, user_id: UUID, password_id: UUID):
        self.user_id = user_id
        self.password_id = password_id
        super().__init__(
            f"User {user_id} does not have permission to access password {password_id}"
        )


class NotPasswordOwnerError(PasswordManagementDomainError):
    """Raised when a non-owner tries to perform owner-only operations"""

    def __init__(self, user_id: UUID, password_id: UUID):
        self.user_id = user_id
        self.password_id = password_id
        super().__init__(f"User {user_id} is not the owner of password {password_id}")


class CannotUnshareWithOwnerError(PasswordManagementDomainError):
    """Raised when trying to unshare a password to an owner"""

    def __init__(self, owner_id: UUID, password_id: UUID):
        self.owner_id = owner_id
        self.password_id = password_id
        super().__init__(
            f"Owner {owner_id} cannot have access revoked from password {password_id}"
        )
