from dataclasses import dataclass


@dataclass
class RefreshAccessTokenCommand:
    refresh_token: str
