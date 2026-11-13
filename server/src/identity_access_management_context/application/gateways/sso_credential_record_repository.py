from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import SSOCredentialRecord


class SSOCredentialRecordRepository(Protocol):
    """Links between an SSO provider's subjects and the users they sign in."""

    def create(self, credential_record: SSOCredentialRecord) -> None: ...
    def update_last_login(self, provider: str, subject: str, last_login: datetime) -> None: ...
    def get_by_subject(self, provider: str, subject: str) -> SSOCredentialRecord | None: ...
    def list_by_principal_id(self, principal_id: UUID) -> list[SSOCredentialRecord]: ...
