from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from identity_access_management_context.domain.entities import SSOCredentialRecord


class SSOCredentialRecordRepository(ABC):
    """Links between an SSO provider's subjects and the users they sign in."""

    @abstractmethod
    def create(self, credential_record: SSOCredentialRecord) -> None: ...

    @abstractmethod
    def update_last_login(self, provider: str, subject: str, last_login: datetime) -> None: ...

    @abstractmethod
    def get_by_subject(self, provider: str, subject: str) -> SSOCredentialRecord | None: ...

    @abstractmethod
    def get_by_principal_id(self, principal_id: UUID) -> SSOCredentialRecord | None: ...
