from typing import Protocol


class VaultSessionGateway(Protocol):
    def store_decrypted_key(self, decrypted_key: str) -> None:
        """Store the decrypted vault key in memory for the session

        Args:
            decrypted_key: The decrypted vault key
        """
        ...

    def get_decrypted_key(self) -> str:
        """Get the decrypted vault key from memory

        Returns:
            The decrypted vault key

        Raises:
            ValueError: If no decrypted key is stored in memory
        """
        ...

    def clear_decrypted_key(self) -> None:
        """Clear the decrypted vault key from memory"""
        ...
