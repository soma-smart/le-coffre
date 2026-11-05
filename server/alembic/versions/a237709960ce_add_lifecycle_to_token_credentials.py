"""add lifecycle to token credentials

Token credential records can expire, go stale when unused, be read-only and
carry a label. Existing records keep working as before: never expiring, never
idle, not read-only.

Revision ID: a237709960ce
Revises: 76b9210560fd
Create Date: 2026-10-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a237709960ce'
down_revision: Union[str, Sequence[str], None] = '76b9210560fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('iam__credential__token') as batch_op:
        batch_op.add_column(sa.Column('read_only', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('label', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_used_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('max_idle_seconds', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('iam__credential__token') as batch_op:
        batch_op.drop_column('max_idle_seconds')
        batch_op.drop_column('last_used_at')
        batch_op.drop_column('expires_at')
        batch_op.drop_column('label')
        batch_op.drop_column('read_only')
