from dataclasses import dataclass


@dataclass
class AuthenticateWithSSOCommand:
    token: str
