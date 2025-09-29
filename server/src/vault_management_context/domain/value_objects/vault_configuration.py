from dataclasses import dataclass, field

from vault_management_context.domain.exceptions import (
    InvalidShareCountError,
    InvalidThresholdError,
    ThresholdExceedsShareCountError,
)


class ShareCount(int):
    """Represents the number of Shamir shares for a vault

    Domain Rules:
    - Must be at least 2 for security reasons
    - Cannot be negative or zero
    """

    def __new__(cls, value: int):
        if value < 2:
            raise InvalidShareCountError(value)
        return int.__new__(cls, value)

    def __str__(self) -> str:
        return str(int(self))


class Threshold(int):
    """Represents the minimum number of shares needed to unlock a vault

    Domain Rules:
    - Must be at least 2 for security reasons
    - Cannot be negative or zero
    """

    def __new__(cls, value: int):
        if value < 2:
            raise InvalidThresholdError(value)
        return int.__new__(cls, value)

    def __str__(self) -> str:
        return str(int(self))


@dataclass(frozen=True)
class VaultConfiguration:
    """Represents a complete vault configuration

    Domain Rules:
    - Threshold cannot exceed ShareCount (would make vault impossible to unlock)
    """

    share_count: ShareCount = field()
    threshold: Threshold = field()

    def __post_init__(self):
        if self.threshold > self.share_count:
            raise ThresholdExceedsShareCountError(self.threshold, self.share_count)

    @classmethod
    def create(cls, nb_shares: int, threshold: int) -> "VaultConfiguration":
        return cls(share_count=ShareCount(nb_shares), threshold=Threshold(threshold))
