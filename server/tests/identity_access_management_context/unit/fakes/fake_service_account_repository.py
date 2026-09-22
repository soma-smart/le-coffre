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

    Refuses the same writes the SQL adapter refuses, or the unit suite would stay
    green while production behaved differently.
    """

    def __init__(self):
        self.accounts: dict[UUID, ServiceAccount] = {}

    def create(self, accounts: Iterable[ServiceAccount]) -> None:
        for account in accounts:
            self.accounts[account.id] = account

    def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[ServiceAccount | None]:
        # One slot per requested id, empty where there is no such account.
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
