from dataclasses import dataclass


@dataclass
class AdminLoginCommand:
    email: str
    password: str
