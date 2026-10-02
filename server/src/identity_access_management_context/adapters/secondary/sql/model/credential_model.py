from enum import StrEnum
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Column, Field

from .iam_table import IAMTable
from .principal_model import PrincipalTable


class CredentialKind(StrEnum):
    """Which per-kind table holds a credential's verifier."""

    PASSWORD = "password"  # noqa: S105
    TOKEN = "token"  # noqa: S105
    SSO = "sso"


class CredentialRecordTable(IAMTable, table=True):
    """Registry of every credential, with the principal it proves.

    A credential cannot outlive its principal: it would be a secret nobody can
    see or revoke, so the principal's deletion takes its credentials with it.
    """

    __table_suffix__ = "credential"

    id: UUID = Field(primary_key=True)
    kind: CredentialKind = Field(
        sa_column=Column(
            sa.Enum(
                CredentialKind,
                name="credential_kind",
                native_enum=False,
                create_constraint=True,
                values_callable=lambda kinds: [kind.value for kind in kinds],
            ),
            nullable=False,
        )
    )
    principal_id: UUID = Field(foreign_key=PrincipalTable.__tablename__ + ".id", ondelete="CASCADE", index=True)


class CredentialRecordDetailsTable(IAMTable):
    """Base for the per-kind tables, named ``iam__credential__<kind>``."""

    __table_suffix__ = CredentialRecordTable.__table_suffix__

    credential_id: UUID = Field(
        primary_key=True, foreign_key=CredentialRecordTable.__tablename__ + ".id", ondelete="CASCADE"
    )
