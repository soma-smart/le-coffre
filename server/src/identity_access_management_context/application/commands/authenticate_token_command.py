from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticateTokenCommand:
    token: str = field(repr=False)
