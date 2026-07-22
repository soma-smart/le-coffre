from dataclasses import dataclass


@dataclass
class LogoutCommand:
    access_token: str
    refresh_token: str
