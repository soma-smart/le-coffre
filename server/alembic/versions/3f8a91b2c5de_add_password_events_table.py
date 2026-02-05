"""add password_events table

Revision ID: 3f8a91b2c5de
Revises: 728072a081f9
Create Date: 2026-01-30 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "3f8a91b2c5de"
down_revision: Union[str, Sequence[str], None] = "728072a081f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "password_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("occurred_on", sa.DateTime(), nullable=False),
        sa.Column("password_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("event_data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        op.f("ix_password_events_event_type"),
        "password_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_events_occurred_on"),
        "password_events",
        ["occurred_on"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_events_password_id"),
        "password_events",
        ["password_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_events_actor_user_id"),
        "password_events",
        ["actor_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_password_events_actor_user_id"), table_name="password_events"
    )
    op.drop_index(op.f("ix_password_events_password_id"), table_name="password_events")
    op.drop_index(op.f("ix_password_events_occurred_on"), table_name="password_events")
    op.drop_index(op.f("ix_password_events_event_type"), table_name="password_events")
    op.drop_table("password_events")
