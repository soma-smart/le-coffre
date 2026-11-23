from dataclasses import dataclass


@dataclass
class SsoLoginCommand:
    code: str
