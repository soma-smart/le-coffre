"""add notification options to one time link

Revision ID: 8a4d2c7e1b93
Revises: 670fae75e21d
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a4d2c7e1b93'
down_revision: Union[str, Sequence[str], None] = '670fae75e21d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default false: every link created before this migration did not ask
    # to be notified, and the NOT NULL columns must be filled for those rows.
    # expiry_notified_at stays NULL until the expiry sweep claims the link.
    with op.batch_alter_table('OneTimeLink') as batch_op:
        batch_op.add_column(
            sa.Column('notify_on_read', sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.add_column(
            sa.Column('notify_on_expiry', sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.add_column(sa.Column('expiry_notified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('OneTimeLink') as batch_op:
        batch_op.drop_column('expiry_notified_at')
        batch_op.drop_column('notify_on_expiry')
        batch_op.drop_column('notify_on_read')
