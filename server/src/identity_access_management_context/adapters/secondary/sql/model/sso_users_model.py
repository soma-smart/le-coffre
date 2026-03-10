from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class SsoUsersTable(SQLModel, table=True):
    __tablename__: str = "SsoUser"

    internal_user_id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    email: str = Field(description="User email", nullable=False)
    display_name: str = Field(description="User display name", nullable=False)
    sso_user_id: str = Field(description="SSO User ID", nullable=False)
    sso_provider: str = Field(description="SSO provider name", default="default", nullable=False)
    created_at: datetime = Field(
        description="Creation timestamp",
        nullable=True,
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_login: datetime | None = Field(
        description="Last login timestamp",
        nullable=True,
        default_factory=lambda: datetime.now(timezone.utc),
    )


def create_sso_user_table(engine):
    SQLModel.metadata.create_all(engine)
