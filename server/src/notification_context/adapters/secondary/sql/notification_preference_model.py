from uuid import UUID

from sqlmodel import Field, SQLModel


class NotificationPreferenceTable(SQLModel, table=True):
    __tablename__: str = "NotificationPreference"

    # No foreign key to User: bounded contexts do not share tables. A deleted
    # user's row is simply never matched again (RecipientGateway skips them).
    user_id: UUID = Field(primary_key=True)
    notify_on_vault_lock: bool = Field(default=False, nullable=False, index=True)
    notify_on_vault_unlock: bool = Field(default=False, nullable=False, index=True)
