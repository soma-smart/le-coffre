"""Add IAM and Vault Events Tables

Revision ID: c3f8a912b047
Revises: aa385458b504
Create Date: 2026-02-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c3f8a912b047'
down_revision: Union[str, Sequence[str], None] = 'aa385458b504'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('iam_events',
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('occurred_on', sa.DateTime(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('event_data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_iam_events_actor_user_id'), 'iam_events', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_iam_events_event_type'), 'iam_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_iam_events_occurred_on'), 'iam_events', ['occurred_on'], unique=False)

    op.create_table('vault_events',
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('occurred_on', sa.DateTime(), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('event_data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_vault_events_actor_user_id'), 'vault_events', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_vault_events_event_type'), 'vault_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_vault_events_occurred_on'), 'vault_events', ['occurred_on'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_vault_events_occurred_on'), table_name='vault_events')
    op.drop_index(op.f('ix_vault_events_event_type'), table_name='vault_events')
    op.drop_index(op.f('ix_vault_events_actor_user_id'), table_name='vault_events')
    op.drop_table('vault_events')

    op.drop_index(op.f('ix_iam_events_occurred_on'), table_name='iam_events')
    op.drop_index(op.f('ix_iam_events_event_type'), table_name='iam_events')
    op.drop_index(op.f('ix_iam_events_actor_user_id'), table_name='iam_events')
    op.drop_table('iam_events')
