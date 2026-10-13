from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Index, and_, false, true
from sqlmodel import DateTime, Field, SQLModel


class OneTimeLinkTable(SQLModel, table=True):
    """SQLModel table for single-use password links.

    Rows survive consumption and revocation so the read stays auditable; only
    the SHA-256 of the token is kept, never the token itself.
    """

    __tablename__: str = "OneTimeLink"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    password_id: UUID = Field(nullable=False, index=True)
    token_hash: str = Field(nullable=False, unique=True, index=True, description="SHA-256 hex of the link token")
    created_by_user_id: UUID = Field(nullable=False, index=True)
    created_at: datetime = Field(sa_type=DateTime, nullable=False)
    expires_at: datetime = Field(sa_type=DateTime, nullable=False, index=True)
    read_at: datetime | None = Field(sa_type=DateTime, default=None, description="When the link was consumed")
    revoked_at: datetime | None = Field(sa_type=DateTime, default=None, description="When the owner revoked the link")
    notify_on_read: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": false()},
        description="The creator asked to be emailed when the link is read",
    )
    notify_on_expiry: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": false()},
        description="The creator asked to be emailed if the link expires unused",
    )
    expiry_notified_at: datetime | None = Field(
        sa_type=DateTime,
        default=None,
        description="When the expiry sweep claimed this link; set at most once",
    )


# The links the expiry sweep is looking for. Shared by the partial index below and
# by the sweep's query: SQLite only uses a partial index when the query repeats its
# predicate term for term, so the two must never be written separately.
PENDING_EXPIRY_NOTIFICATION = and_(
    OneTimeLinkTable.notify_on_expiry == true(),  # type: ignore[arg-type]
    OneTimeLinkTable.expiry_notified_at.is_(None),  # type: ignore[union-attr]
    OneTimeLinkTable.read_at.is_(None),  # type: ignore[union-attr]
    OneTimeLinkTable.revoked_at.is_(None),  # type: ignore[union-attr]
)

# The table is never purged: without this, every sweep pass would walk every link
# that ever expired to find the few still waiting for their notification.
Index(
    "ix_OneTimeLink_pending_expiry_notification",
    OneTimeLinkTable.expires_at,
    sqlite_where=PENDING_EXPIRY_NOTIFICATION,
    postgresql_where=PENDING_EXPIRY_NOTIFICATION,
)
