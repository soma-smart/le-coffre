"""add expires_at to permission

Revision ID: b7c1e9f4a2d8
Revises: fdda4ddd2859
Create Date: 2026-07-27 10:12:04.118273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1e9f4a2d8'
down_revision: Union[str, Sequence[str], None] = 'fdda4ddd2859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable on purpose: NULL means "permanent", which is what every share
    # created before temporary sharing existed is.
    op.add_column('Permission', sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_Permission_expires_at'), 'Permission', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_Permission_expires_at'), table_name='Permission')
    op.drop_column('Permission', 'expires_at')
