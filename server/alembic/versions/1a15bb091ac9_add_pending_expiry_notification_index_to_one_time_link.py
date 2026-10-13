"""add pending expiry notification index to one time link

Revision ID: 1a15bb091ac9
Revises: 8a4d2c7e1b93
Create Date: 2026-10-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a15bb091ac9'
down_revision: Union[str, Sequence[str], None] = '8a4d2c7e1b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Partial index serving the expiry sweep, which otherwise walks every link that ever
# expired. The predicate must stay term for term the one the sweep's query renders
# (PENDING_EXPIRY_NOTIFICATION in the model), or SQLite will not use the index.
_PENDING_COLUMNS = 'expiry_notified_at IS NULL AND read_at IS NULL AND revoked_at IS NULL'


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'ix_OneTimeLink_pending_expiry_notification',
        'OneTimeLink',
        ['expires_at'],
        unique=False,
        sqlite_where=sa.text(f'notify_on_expiry = 1 AND {_PENDING_COLUMNS}'),
        postgresql_where=sa.text(f'notify_on_expiry = true AND {_PENDING_COLUMNS}'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_OneTimeLink_pending_expiry_notification', table_name='OneTimeLink')
