from typing import Optional
from sqlmodel import CheckConstraint, SQLModel, Field
from uuid import UUID
from datetime import datetime


class SsoUsersTable(SQLModel, table=True):
    __tablename__ = "SsoUsersTable"

    internal_user_id: UUID = Field(default_factory=UUID, nullable=False, primary_key=True, index=True)
    email: str = Field(description="User email", nullable=False)
    sso_user_id: str = Field(description="SSO User ID", nullable=False)
    sso_provider: str = Field(description="Password name", default="default", nullable=False)
    created_at: datetime = Field(description="Creation timestamp", nullable=False, default=datetime.timezone.utc.now)
    last_login: datetime = Field(description="Last login timestamp", nullable=True)


def create_password_table(engine):
    SQLModel.metadata.create_all(engine)
    