from datetime import datetime

from sqlmodel import Field

from .principal_model import PrincipalDetailsTable, PrincipalKind


class UserPrincipalTable(PrincipalDetailsTable, table=True):
    """A user's details, keyed by its row in the principal registry."""

    __table_suffix__ = PrincipalKind.USER.value

    username: str = Field(nullable=False)
    email: str = Field(nullable=False)
    name: str = Field(nullable=False)
    roles: str = Field(default="[]", description="Roles as JSON string")
    current_refresh_token_jti: str | None = Field(default=None, nullable=True)
    session_invalid_before: datetime | None = Field(default=None, nullable=True)
