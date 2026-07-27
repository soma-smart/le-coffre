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
            f"Password is too short: {current_length} characters. Minimum required: {min_length} characters"
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


class PasswordEncryptionUnavailableError(PasswordManagementDomainError):
    """Raised when the vault is locked and encryption/decryption cannot be performed"""

    def __init__(self):
        super().__init__("Vault is locked: unlock the vault to perform this operation")


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
        super().__init__(f"User {user_id} does not have permission to access password {password_id}")


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
        super().__init__(f"Owner {owner_id} cannot have access revoked from password {password_id}")


# One-time link exceptions
#
# The four "not consumable" errors below are deliberately distinct so the domain
# and the tests can tell them apart, but the consume route collapses all of them
# into an identical 404. Distinguishing them over the wire would turn the
# anonymous endpoint into an oracle telling an attacker whether a token exists.


class OneTimeLinkNotFoundError(PasswordManagementDomainError):
    """Raised when no one-time link matches the presented token"""

    def __init__(self) -> None:
        super().__init__("The one-time link does not exist")


class OneTimeLinkExpiredError(PasswordManagementDomainError):
    """Raised when a one-time link is presented after its expiry date"""

    def __init__(self) -> None:
        super().__init__("The one-time link has expired")


class OneTimeLinkAlreadyUsedError(PasswordManagementDomainError):
    """Raised when a one-time link is presented a second time"""

    def __init__(self) -> None:
        super().__init__("The one-time link has already been used")


class OneTimeLinkRevokedError(PasswordManagementDomainError):
    """Raised when a one-time link was revoked by its owner"""

    def __init__(self) -> None:
        super().__init__("The one-time link has been revoked")


class InvalidOneTimeLinkTokenError(PasswordManagementDomainError):
    """Raised when a presented token is too short to have been generated by us"""

    def __init__(self) -> None:
        super().__init__("The one-time link token is malformed")


class TooManyActiveOneTimeLinksError(PasswordManagementDomainError):
    """Raised when a password already has the maximum of outstanding usable links"""

    def __init__(self, active_count: int, max_active: int):
        self.active_count = active_count
        self.max_active = max_active
        super().__init__(
            f"This password already has {active_count} active one-time links "
            f"(maximum {max_active}). Revoke one before creating another."
        )


class OneTimeLinkLifetimeTooShortError(PasswordManagementDomainError):
    """Raised when the requested lifetime is below the allowed minimum"""

    def __init__(self, requested_seconds: int, min_seconds: int):
        self.requested_seconds = requested_seconds
        self.min_seconds = min_seconds
        super().__init__(f"Lifetime is too short: {requested_seconds}s. Minimum allowed: {min_seconds}s")


class OneTimeLinkLifetimeTooLongError(PasswordManagementDomainError):
    """Raised when the requested lifetime is above the allowed maximum"""

    def __init__(self, requested_seconds: int, max_seconds: int):
        self.requested_seconds = requested_seconds
        self.max_seconds = max_seconds
        super().__init__(f"Lifetime is too long: {requested_seconds}s. Maximum allowed: {max_seconds}s")
