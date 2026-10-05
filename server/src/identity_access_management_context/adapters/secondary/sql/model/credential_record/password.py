from sqlmodel import Field

from ._credential_record import CredentialKind, CredentialRecordDetailsTable


class PasswordCredentialRecordTable(CredentialRecordDetailsTable, table=True):
    __table_suffix__ = CredentialKind.PASSWORD.value

    email: str = Field(nullable=False, unique=True, description="Email the user logs in with")
    password_hash: bytes = Field(nullable=False, description="Hashed user password")
