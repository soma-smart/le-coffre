from typing import Protocol


class EncryptionGateway(Protocol):
    def generate_vault_key(self, master_key: str) -> str:
        """Generate a random vault key and encrypt it using the master key

        Args:
            master_key: The key used to encrypt

        Returns:
            The encrypted vault key
        """
        ...

    def encrypt(self, decrypted_data: str, master_key: str) -> str:
        """Encrypt data using the master key

        Args:
            decrypted_data: The data to encrypt
            master_key: The key used to encrypt

        Returns:
            The encrypted data
        """
        ...

    def decrypt(self, encrypted_data: str, master_key: str) -> str:
        """Decrypt data using the master key

        Args:
            encrypted_data: The data to decrypt
            master_key: The key used to decrypt

        Returns:
            The decrypted data
        """
        ...
