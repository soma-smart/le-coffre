class VaultManagementDomainError(Exception):
    """Base exception for all vault management domain errors"""

    pass


class VaultAlreadyExistsError(VaultManagementDomainError):
    """Raised when attempting to create a vault that already exists"""

    def __init__(self):
        super().__init__("A vault has already been created for this organization")


class InvalidShareCountError(VaultManagementDomainError):
    """Raised when share count doesn't meet security requirements"""

    def __init__(self, share_count: int):
        super().__init__(
            f"Share count must be at least 2 for security reasons, got {share_count}"
        )


class InvalidThresholdError(VaultManagementDomainError):
    """Raised when threshold doesn't meet security requirements"""

    def __init__(self, threshold: int):
        super().__init__(
            f"Threshold must be at least 2 to ensure security, got {threshold}"
        )


class ThresholdExceedsShareCountError(VaultManagementDomainError):
    """Raised when threshold is impossible to satisfy given share count"""

    def __init__(self, threshold: int, share_count: int):
        super().__init__(
            f"Threshold {threshold} cannot exceed share count {share_count} - impossible to unlock vault"
        )
