from sqlmodel import Field

from .credential_model import CredentialKind, CredentialRecordDetailsTable


class ServiceAccountTokenCredentialRecordTable(CredentialRecordDetailsTable, table=True):
    __table_suffix__ = CredentialKind.SERVICE_ACCOUNT_TOKEN.value

    token_hash: str = Field(
        nullable=False, unique=True, index=True, description="SHA-256 hex of the service account token"
    )
