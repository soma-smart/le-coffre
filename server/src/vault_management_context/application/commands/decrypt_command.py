from dataclasses import dataclass


@dataclass
class DecryptCommand:
    encrypted_data: str
