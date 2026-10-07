"""add notification preference table

Revision ID: 670fae75e21d
Revises: 6f3f296a75c9
Create Date: 2026-09-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '670fae75e21d'
down_revision: Union[str, Sequence[str], None] = '6f3f296a75c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No row means every notification is off: users opt in from their profile.
    op.create_table(
        'NotificationPreference',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('notify_on_vault_lock', sa.Boolean(), nullable=False),
        sa.Column('notify_on_vault_unlock', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_index(
        op.f('ix_NotificationPreference_notify_on_vault_lock'),
        'NotificationPreference',
        ['notify_on_vault_lock'],
        unique=False,
    )
    op.create_index(
        op.f('ix_NotificationPreference_notify_on_vault_unlock'),
        'NotificationPreference',
        ['notify_on_vault_unlock'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_NotificationPreference_notify_on_vault_unlock'), table_name='NotificationPreference')
    op.drop_index(op.f('ix_NotificationPreference_notify_on_vault_lock'), table_name='NotificationPreference')
    op.drop_table('NotificationPreference')
