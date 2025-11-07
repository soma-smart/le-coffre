from dataclasses import dataclass


@dataclass(frozen=True)
class AccessToken:
    value: str
    expiration_minutes: int

    def __post_init__(self):
        if not self.value:
            raise ValueError("Access token value cannot be empty")
        if self.expiration_minutes <= 0:
            raise ValueError("Expiration minutes must be positive")

    def __str__(self) -> str:
        return self.value
