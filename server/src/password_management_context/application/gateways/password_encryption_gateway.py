from typing import Protocol


class PasswordEncryptionGateway(Protocol):
    def encrypt(self, password: str) -> str:
        """Encrypts the given password."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts the given ciphertext."""
        ...
