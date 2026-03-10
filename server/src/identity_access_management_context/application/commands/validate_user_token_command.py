from dataclasses import dataclass


@dataclass
class ValidateUserTokenCommand:
    jwt_token: str
    required_roles: list[str] | None = None
