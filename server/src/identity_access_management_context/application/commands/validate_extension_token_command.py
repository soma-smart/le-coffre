from dataclasses import dataclass


@dataclass
class ValidateExtensionTokenCommand:
    raw_token: str
