from enum import StrEnum
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Column, Field

from .iam_table import IAMTable


class PrincipalKind(StrEnum):
    """Which per-kind table holds a principal's details."""

    USER = "user"
    SERVICE_ACCOUNT = "service_account"


class PrincipalTable(IAMTable, table=True):
    """Registry of every principal, whatever its kind.

    One row per principal is what keeps ids unique across kinds; the kind
    names the table holding the rest of it.
    """

    __table_suffix__ = "principal"

    id: UUID = Field(primary_key=True)
    kind: PrincipalKind = Field(
        sa_column=Column(
            sa.Enum(
                PrincipalKind,
                name="principal_kind",
                native_enum=False,
                create_constraint=True,
                values_callable=lambda kinds: [kind.value for kind in kinds],
            ),
            nullable=False,
        )
    )


class PrincipalDetailsTable(IAMTable):
    """Base for the per-kind tables, named ``iam__principal__<kind>``."""

    __table_suffix__ = PrincipalTable.__table_suffix__

    principal_id: UUID = Field(primary_key=True, foreign_key=PrincipalTable.__tablename__ + ".id")
