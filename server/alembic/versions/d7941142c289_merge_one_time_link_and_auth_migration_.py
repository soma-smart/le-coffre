"""merge one-time-link and auth migration heads

Revision ID: d7941142c289
Revises: 91d77868648a, f1a2b3c4d5e6
Create Date: 2026-07-24 15:28:18.658580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd7941142c289'
down_revision: Union[str, Sequence[str], None] = ('91d77868648a', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
