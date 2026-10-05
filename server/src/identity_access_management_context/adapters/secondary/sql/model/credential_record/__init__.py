from ._credential_record import CredentialKind, CredentialRecordTable
from .password import PasswordCredentialRecordTable
from .sso import SSOCredentialRecordTable
from .token import TokenCredentialRecordTable

__all__ = (
    "CredentialRecordTable",
    "CredentialKind",
    "PasswordCredentialRecordTable",
    "SSOCredentialRecordTable",
    "TokenCredentialRecordTable",
)

CREDENTIAL_DETAILS_TABLES = frozenset(
    (
        PasswordCredentialRecordTable,
        SSOCredentialRecordTable,
        TokenCredentialRecordTable,
    )
)
