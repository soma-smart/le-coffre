from typing import Protocol


class EncryptionService(Protocol):
    def encrypt(self, plaintext: str) -> str:
        """Encrypts the given plaintext."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts the given ciphertext."""
        ...
