from dataclasses import dataclass


@dataclass
class UpdateUserPasswordResponse:
    access_token: str
    refresh_token: str
