from dataclasses import dataclass


@dataclass(frozen=True)
class RefreshToken:
    value: str
    expiration_days: int

    def __post_init__(self):
        if not self.value:
            raise ValueError("Refresh token value cannot be empty")
        if self.expiration_days <= 0:
            raise ValueError("Expiration days must be positive")

    def __str__(self) -> str:
        return self.value
