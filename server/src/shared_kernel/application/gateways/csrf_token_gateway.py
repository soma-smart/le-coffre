from typing import Protocol
from uuid import UUID


class CsrfTokenGateway(Protocol):
    """
    Gateway for CSRF token management.
    Provides synchronizer token pattern for CSRF protection.
    """

    def generate_token(self, user_id: UUID) -> str:
        """
        Generate a new CSRF token for the given user.
        Overwrites any existing token for this user.

        Args:
            user_id: The user's unique identifier

        Returns:
            The generated CSRF token
        """
        ...

    def validate_token(self, user_id: UUID, token: str) -> bool:
        """
        Validate a CSRF token for the given user.

        Args:
            user_id: The user's unique identifier
            token: The CSRF token to validate

        Returns:
            True if the token is valid and not expired, False otherwise
        """
        ...

    def delete_token(self, user_id: UUID) -> None:
        """
        Delete the CSRF token for the given user (e.g., on logout).

        Args:
            user_id: The user's unique identifier
        """
        ...
