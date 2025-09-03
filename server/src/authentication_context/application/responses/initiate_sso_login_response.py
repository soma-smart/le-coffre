from dataclasses import dataclass


@dataclass
class InitiateSSOLoginResponse:
    authorization_url: str
    state: str
