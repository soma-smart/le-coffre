"""CSRF token management using the Synchronizer Token Pattern."""

import secrets
from uuid import UUID


class CsrfTokenManager:
    """
    Manages CSRF tokens for authenticated users.

    Tokens are stored in-memory and remain valid for the entire user session.
    Each user (identified by UUID) can have one active CSRF token.
    """

    def __init__(self):
        self._tokens: dict[UUID, str] = {}

    def generate_token(self, user_id: UUID) -> str:
        """
        Generate a new CSRF token for a user.

        If the user already has a token, it is replaced with a new one.
        Uses secrets.token_urlsafe for cryptographic randomness.
        """
        token = secrets.token_urlsafe(32)
        self._tokens[user_id] = token
        return token

    def validate_token(self, user_id: UUID, token: str) -> bool:
        """
        Validate a CSRF token for a user.

        Uses constant-time comparison to prevent timing attacks.
        Returns True if the token matches, False otherwise.
        """
        stored_token = self._tokens.get(user_id)
        if stored_token is None:
            return False
        return secrets.compare_digest(stored_token, token)

    def delete_token(self, user_id: UUID) -> None:
        """Delete the CSRF token for a user (e.g., on logout)."""
        self._tokens.pop(user_id, None)
