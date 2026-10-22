"""add one time link subscription table

Revision ID: 55a7d471ce68
Revises: 670fae75e21d
Create Date: 2026-10-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55a7d471ce68'
down_revision: Union[str, Sequence[str], None] = '670fae75e21d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # A row lives only until its link is read or has expired: the expiry sweep looks
    # them up by expires_at.
    op.create_table(
        'OneTimeLinkSubscription',
        sa.Column('link_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('notify_on_read', sa.Boolean(), nullable=False),
        sa.Column('notify_on_expiry', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('link_id'),
    )
    op.create_index(
        op.f('ix_OneTimeLinkSubscription_expires_at'),
        'OneTimeLinkSubscription',
        ['expires_at'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_OneTimeLinkSubscription_expires_at'), table_name='OneTimeLinkSubscription')
    op.drop_table('OneTimeLinkSubscription')
