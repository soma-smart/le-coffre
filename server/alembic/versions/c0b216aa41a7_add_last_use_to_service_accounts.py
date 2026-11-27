"""add last use to service accounts

A service account now records when one of its tokens last authenticated, so
its owner can tell a dormant account from a live one. Kept on the account
rather than read from its token record: revoking deletes the token record, and
an inventory still has to tell how long a revoked account had been dormant.

Filled from the token records that exist. An account revoked before has none
left: its last use is unknown and stays empty.

Revision ID: c0b216aa41a7
Revises: d5a8c3f1e7b9
Create Date: 2026-11-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0b216aa41a7'
down_revision: Union[str, Sequence[str], None] = 'd5a8c3f1e7b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('iam__principal__service_account') as batch_op:
        batch_op.add_column(sa.Column('last_used_at', sa.DateTime(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE iam__principal__service_account SET last_used_at = (
                SELECT MAX(token.last_used_at)
                FROM iam__credential__token AS token
                JOIN iam__credential AS credential ON credential.id = token.credential_id
                WHERE credential.principal_id = iam__principal__service_account.principal_id
            )
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('iam__principal__service_account') as batch_op:
        batch_op.drop_column('last_used_at')
