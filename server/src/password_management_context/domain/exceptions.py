from uuid import UUID
from typing import List


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


class PasswordMultipleComplexityError(PasswordComplexityError):
    """Raised when password has multiple complexity violations"""

    def __init__(self, violations: List[PasswordComplexityError]):
        self.violations = violations
        messages = [str(violation) for violation in violations]
        super().__init__(
            f"Password has multiple complexity violations: {'; '.join(messages)}"
        )


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
