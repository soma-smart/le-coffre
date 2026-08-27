from datetime import datetime, timedelta
from uuid import UUID

from identity_access_management_context.domain.entities import ExtensionToken


class FakeExtensionTokenRepository:
    def __init__(self):
        self.tokens: dict[UUID, ExtensionToken] = {}
        # Records every touch_last_used call, including the ones the coarsening
        # window swallows, so a test can assert on the attempt as well as the
        # effect.
        self.touch_calls: list[tuple[UUID, datetime]] = []
        self.raise_on_touch = False

    def add(self, token: ExtensionToken) -> ExtensionToken:
        self.tokens[token.id] = token
        return token

    def get_by_token_hash(self, token_hash: str) -> ExtensionToken | None:
        for token in self.tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    def get_by_id(self, token_id: UUID) -> ExtensionToken | None:
        return self.tokens.get(token_id)

    def list_for_user(self, user_id: UUID) -> list[ExtensionToken]:
        return sorted(
            (token for token in self.tokens.values() if token.user_id == user_id),
            key=lambda token: token.created_at,
            reverse=True,
        )

    def count_active_for_user(self, user_id: UUID, now: datetime) -> int:
        return sum(1 for token in self.tokens.values() if token.user_id == user_id and token.is_active(now))

    def revoke(self, token_id: UUID, now: datetime) -> bool:
        token = self.tokens.get(token_id)
        if token is None or token.is_revoked():
            return False
        token.revoke(now)
        return True

    def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        revoked = 0
        for token in self.tokens.values():
            if token.user_id == user_id and not token.is_revoked():
                token.revoke(now)
                revoked += 1
        return revoked

    def touch_last_used(self, token_id: UUID, now: datetime, coarsen_to_seconds: int) -> None:
        self.touch_calls.append((token_id, now))
        if self.raise_on_touch:
            raise RuntimeError("storage unavailable")

        token = self.tokens.get(token_id)
        if token is None:
            return
        threshold = now - timedelta(seconds=coarsen_to_seconds)
        if token.last_used_at is None or token.last_used_at < threshold:
            token.last_used_at = now
