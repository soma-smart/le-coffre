"""make user emails unique

An email identifies one person: one user per email, whether it signs in with a
password or through SSO. Existing duplicates are not merged here, which account
should survive is not something a migration can decide: the upgrade stops and
names them, for an operator to resolve before running it again.

Revision ID: f2c8a61d4b07
Revises: e41b6f0c2d93
Create Date: 2026-10-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c8a61d4b07'
down_revision: Union[str, Sequence[str], None] = 'e41b6f0c2d93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                'SELECT email, COUNT(*) FROM iam__principal__user GROUP BY email HAVING COUNT(*) > 1 ORDER BY email'
            )
        )
        .all()
    )
    if duplicates:
        listed = ", ".join(f"{email} ({count} users)" for email, count in duplicates)
        raise RuntimeError(
            "Cannot make user emails unique: several users share an email. "
            f"Give each of them a distinct email, or delete the extra accounts, then upgrade again: {listed}"
        )

    op.create_index(
        op.f('ix_iam__principal__user_email'), 'iam__principal__user', ['email'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_iam__principal__user_email'), table_name='iam__principal__user')
