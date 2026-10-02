from sqlmodel import Field

from .credential_model import CredentialKind, CredentialRecordDetailsTable


class PasswordCredentialRecordTable(CredentialRecordDetailsTable, table=True):
    __table_suffix__ = CredentialKind.PASSWORD.value

    email: str = Field(nullable=False, description="Email the user logs in with")
    password_hash: bytes = Field(nullable=False, description="Hashed user password")
