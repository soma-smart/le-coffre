"""CSRF token management using the Synchronizer Token Pattern."""

import secrets
from collections import deque
from uuid import UUID

# How many concurrently valid tokens one user may hold.
#
# One token per user was the original design, and it quietly made the app
# single-tab. Every fresh tab fetches a token through the router guard, and the
# browser extension's approval page does the same; issuing one replaced the
# token every other open tab was still holding, so the next POST from an older
# tab failed with "Invalid or expired CSRF token" with nothing on screen to
# explain it.
#
# A small ring of recent tokens does not weaken the pattern. The protection
# comes from the attacker being unable to READ any token: they live in the
# page's memory, never in a cookie, and a cross-origin page cannot make the
# browser attach the header. Whether the server accepts one or ten of them
# changes nothing for an attacker holding none.
MAX_TOKENS_PER_USER = 10


class CsrfTokenManager:
    """
    Manages CSRF tokens for authenticated users.

    Tokens are stored in-memory and remain valid for the entire user session.
    Each user keeps up to ``max_tokens_per_user`` recent tokens, so several tabs
    can hold a valid one at the same time; the oldest is evicted beyond that,
    which bounds a store that has no expiry of its own.
    """

    def __init__(self, max_tokens_per_user: int = MAX_TOKENS_PER_USER):
        self._tokens: dict[UUID, deque[str]] = {}
        self._max_tokens_per_user = max_tokens_per_user

    def generate_token(self, user_id: UUID) -> str:
        """
        Generate a new CSRF token for a user.

        Earlier tokens stay valid until they age out of the ring, so issuing one
        in a new tab does not disarm the tabs already open.
        Uses secrets.token_urlsafe for cryptographic randomness.
        """
        token = secrets.token_urlsafe(32)
        tokens = self._tokens.setdefault(user_id, deque(maxlen=self._max_tokens_per_user))
        tokens.append(token)
        return token

    def validate_token(self, user_id: UUID, token: str) -> bool:
        """
        Validate a CSRF token for a user.

        Uses constant-time comparison to prevent timing attacks. Every stored
        token is compared rather than stopping at the first match, so the
        duration reveals how many tokens the user holds but never which one
        matched, nor anything about their contents.
        """
        tokens = self._tokens.get(user_id)
        if not tokens:
            return False

        matched = False
        for stored_token in tokens:
            if secrets.compare_digest(stored_token, token):
                matched = True
        return matched

    def delete_token(self, user_id: UUID) -> None:
        """Delete every CSRF token for a user (e.g., on logout)."""
        self._tokens.pop(user_id, None)
