from dataclasses import dataclass


@dataclass
class LogoutCommand:
    access_token: str | None
    refresh_token: str
