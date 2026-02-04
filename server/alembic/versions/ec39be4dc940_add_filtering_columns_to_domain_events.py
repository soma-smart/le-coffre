"""add_filtering_columns_to_domain_events

Revision ID: ec39be4dc940
Revises: 67daeaee83eb
Create Date: 2026-02-04 15:35:38.336307

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ec39be4dc940"
down_revision: Union[str, Sequence[str], None] = "67daeaee83eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns for efficient filtering
    op.add_column(
        "DomainEventTable", sa.Column("bounded_context", sa.String(), nullable=True)
    )
    op.add_column(
        "DomainEventTable", sa.Column("actor_user_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "DomainEventTable", sa.Column("target_entity_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "DomainEventTable", sa.Column("target_entity_type", sa.String(), nullable=True)
    )

    # Create indexes for efficient filtering
    op.create_index(
        "ix_DomainEventTable_actor_user_id",
        "DomainEventTable",
        ["actor_user_id", "occurred_on"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_DomainEventTable_target_entity",
        "DomainEventTable",
        ["target_entity_id", "target_entity_type", "occurred_on"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_DomainEventTable_bounded_context",
        "DomainEventTable",
        ["bounded_context", "event_type", "occurred_on"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_DomainEventTable_bounded_context", table_name="DomainEventTable")
    op.drop_index("ix_DomainEventTable_target_entity", table_name="DomainEventTable")
    op.drop_index("ix_DomainEventTable_actor_user_id", table_name="DomainEventTable")

    # Drop columns
    op.drop_column("DomainEventTable", "target_entity_type")
    op.drop_column("DomainEventTable", "target_entity_id")
    op.drop_column("DomainEventTable", "actor_user_id")
    op.drop_column("DomainEventTable", "bounded_context")
