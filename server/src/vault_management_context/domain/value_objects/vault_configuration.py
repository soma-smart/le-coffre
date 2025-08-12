from dataclasses import dataclass, field

from vault_management_context.domain.exceptions import (
    InvalidShareCountError,
    InvalidThresholdError,
    ThresholdExceedsShareCountError,
)


@dataclass(frozen=True)
class ShareCount:
    """Represents the number of Shamir shares for a vault

    Domain Rules:
    - Must be at least 2 for security reasons
    - Cannot be negative or zero
    """

    value: int = field()

    def __post_init__(self):
        if self.value < 2:
            raise InvalidShareCountError(self.value)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Threshold:
    """Represents the minimum number of shares needed to unlock a vault

    Domain Rules:
    - Must be at least 2 for security reasons
    - Cannot be negative or zero
    """

    value: int = field()

    def __post_init__(self):
        if self.value < 2:
            raise InvalidThresholdError(self.value)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class VaultConfiguration:
    """Represents a complete vault configuration

    Domain Rules:
    - Threshold cannot exceed ShareCount (would make vault impossible to unlock)
    """

    share_count: ShareCount = field()
    threshold: Threshold = field()

    def __post_init__(self):
        if self.threshold.value > self.share_count.value:
            raise ThresholdExceedsShareCountError(
                self.threshold.value, self.share_count.value
            )

    @classmethod
    def create(cls, nb_shares: int, threshold: int) -> "VaultConfiguration":
        return cls(share_count=ShareCount(nb_shares), threshold=Threshold(threshold))
