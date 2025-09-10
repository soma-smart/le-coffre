from dataclasses import dataclass


@dataclass
class UpdateUserCommand:
    username: str
    email: str
    password: str
