"""add vault share link table

Revision ID: a4e2c6d8f013
Revises: b7c1e9f4a2d8
Create Date: 2026-10-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a4e2c6d8f013'
down_revision: Union[str, Sequence[str], None] = 'b7c1e9f4a2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('VaultShareLink',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('setup_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('share_index', sa.Integer(), nullable=False),
    sa.Column('lookup_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('sealed_share', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_VaultShareLink_expires_at'), 'VaultShareLink', ['expires_at'], unique=False)
    op.create_index(op.f('ix_VaultShareLink_lookup_hash'), 'VaultShareLink', ['lookup_hash'], unique=True)
    op.create_index(op.f('ix_VaultShareLink_setup_id'), 'VaultShareLink', ['setup_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_VaultShareLink_setup_id'), table_name='VaultShareLink')
    op.drop_index(op.f('ix_VaultShareLink_lookup_hash'), table_name='VaultShareLink')
    op.drop_index(op.f('ix_VaultShareLink_expires_at'), table_name='VaultShareLink')
    op.drop_table('VaultShareLink')
