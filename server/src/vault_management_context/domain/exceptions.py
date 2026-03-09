class VaultManagementDomainError(Exception):
    """Base exception for all vault management domain errors"""

    pass


class VaultAlreadyExistsError(VaultManagementDomainError):
    """Raised when attempting to create a vault that already exists"""

    def __init__(self):
        super().__init__("A vault has already been created for this organization")


class VaultNotSetupException(VaultManagementDomainError):
    """Raised when attempting to access a vault that has not been setup yet"""

    def __init__(self):
        super().__init__("Vault has not been setup yet")


class VaultLockedException(VaultManagementDomainError):
    """Raised when attempting to lock a vault that is already locked"""

    def __init__(self):
        super().__init__("Vault is already locked")


class VaultUnlockedError(VaultManagementDomainError):
    """Raised when attempting to unlock a vault already unlocked"""

    def __init__(self):
        super().__init__("Vault is already unlocked")


class ShareReconstructionError(VaultManagementDomainError):
    def __init__(self, message: str = "Failed to reconstruct secret from provided shares"):
        super().__init__(message)


class InvalidShareCountError(VaultManagementDomainError):
    """Raised when share count doesn't meet security requirements"""

    def __init__(self, share_count: int):
        super().__init__(f"Share count must be at least 2 for security reasons, got {share_count}")


class InvalidThresholdError(VaultManagementDomainError):
    """Raised when threshold doesn't meet security requirements"""

    def __init__(self, threshold: int):
        super().__init__(f"Threshold must be at least 2 to ensure security, got {threshold}")


class ThresholdExceedsShareCountError(VaultManagementDomainError):
    """Raised when threshold is impossible to satisfy given share count"""

    def __init__(self, threshold: int, share_count: int):
        super().__init__(f"Threshold {threshold} cannot exceed share count {share_count} - impossible to unlock vault")


class NoVaultExisting(VaultManagementDomainError):
    """Raised when no vault exists for validation"""

    def __init__(self):
        super().__init__("No vault found")


class VaultAlreadySetuped(VaultManagementDomainError):
    """Raised when attempting to validate a vault that is already setup"""

    def __init__(self):
        super().__init__("Vault is not in pending state")


class VaultSetupIdNotFound(VaultManagementDomainError):
    """Raised when the provided setup ID doesn't match the vault's setup ID"""

    def __init__(self):
        super().__init__("Invalid setup ID")
