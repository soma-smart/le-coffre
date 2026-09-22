from collections.abc import Iterable, Sequence
from datetime import datetime
from uuid import UUID

from identity_access_management_context.application.gateways import (
    CannotRevokeServiceAccount,
    CannotRotateServiceAccount,
    ServiceAccountRepository,
)
from identity_access_management_context.domain.entities import ServiceAccount


class FakeServiceAccountRepository(ServiceAccountRepository):
    """In-memory service account repository for testing.

    Reproduces the refusals the SQL adapter makes rather than accepting every
    write: rotating or revoking an already-revoked account raises, and the whole
    batch is refused before anything is applied. A fake that let those through
    would keep the unit suite green while production behaved differently.
    """

    def __init__(self):
        self.accounts: dict[UUID, ServiceAccount] = {}

    def create(self, accounts: Iterable[ServiceAccount]) -> None:
        for account in accounts:
            self.accounts[account.id] = account

    def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[ServiceAccount | None]:
        # One slot per requested id, None where there is no such account, so a
        # caller can destructure the result positionally.
        return [self.accounts.get(account_id) for account_id in ids]

    def list_for_group(self, group_id: UUID) -> Iterable[ServiceAccount]:
        return [account for account in self.accounts.values() if account.group_id == group_id]

    def rotate(self, ids: Sequence[UUID], hashes: Sequence[str]) -> None:
        for account_id in ids:
            account = self.accounts.get(account_id)
            if account is None or not account.is_active:
                raise CannotRotateServiceAccount(account_id)
        for account_id, token_hash in zip(ids, hashes, strict=True):
            self.accounts[account_id].token_hash = token_hash

    def revoke(self, ids: Iterable[UUID], now: datetime) -> None:
        ids = list(ids)
        for account_id in ids:
            account = self.accounts.get(account_id)
            if account is None or not account.is_active:
                raise CannotRevokeServiceAccount(account_id)
        for account_id in ids:
            self.accounts[account_id].revoked_at = now
