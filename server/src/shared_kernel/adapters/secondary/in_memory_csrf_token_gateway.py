import secrets
from typing import Dict
from uuid import UUID

from shared_kernel.application.gateways import CsrfTokenGateway


class InMemoryCsrfTokenGateway(CsrfTokenGateway):
    """
    In-memory implementation of CSRF token storage.

    Tokens are valid for the entire user session (no expiration).
    They are only invalidated when explicitly deleted (e.g., on logout)
    or when a new token is generated for the same user.

    Note: This implementation loses tokens on server restart. For production
    with multiple instances, consider using Redis or a similar shared cache.
    """

    def __init__(self):
        """
        Initialize the CSRF token gateway.
        """
        self._tokens: Dict[UUID, str] = {}

    def generate_token(self, user_id: UUID) -> str:
        """Generate a cryptographically secure random token."""
        token = secrets.token_urlsafe(32)
        self._tokens[user_id] = token
        return token

    def validate_token(self, user_id: UUID, token: str) -> bool:
        """Validate token for the given user."""
        if user_id not in self._tokens:
            return False

        stored_token = self._tokens[user_id]

        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(stored_token, token)

    def delete_token(self, user_id: UUID) -> None:
        """Delete token for user."""
        self._tokens.pop(user_id, None)
