from sqlmodel import Field

from ._credential_record import CredentialKind, CredentialRecordDetailsTable


class TokenCredentialRecordTable(CredentialRecordDetailsTable, table=True):
    __table_suffix__ = CredentialKind.TOKEN.value

    token_hash: str = Field(nullable=False, unique=True, index=True, description="SHA-256 hex of the token")
