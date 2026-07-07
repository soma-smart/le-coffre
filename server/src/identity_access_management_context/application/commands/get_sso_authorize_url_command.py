from dataclasses import dataclass


@dataclass
class GetSsoAuthorizeUrlCommand:
    state: str | None = None
