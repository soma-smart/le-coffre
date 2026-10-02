"""rename user columns to principal

Columns that hold any principal, not only a user, are named for it:
group membership, the personal-group owner, sessions, revoked tokens,
event actors and one-time-link creators. Stored event payloads keep their keys until the API follows.

Revision ID: 83cc85f63482
Revises: 528c0676a893
Create Date: 2026-10-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '83cc85f63482'
down_revision: Union[str, Sequence[str], None] = '528c0676a893'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, old column, new column): every one is indexed as ix_<table>_<column>.
RENAMES = (
    ('GroupMember', 'user_id', 'principal_id'),
    ('Group', 'user_id', 'principal_id'),
    ('AuthSession', 'user_id', 'principal_id'),
    ('RevokedToken', 'user_id', 'principal_id'),
    ('IamEvent', 'actor_user_id', 'actor_principal_id'),
    ('PasswordEvent', 'actor_user_id', 'actor_principal_id'),
    ('OneTimeLink', 'created_by_user_id', 'created_by_principal_id'),
)


def _rename(table: str, old: str, new: str) -> None:
    with op.batch_alter_table(table) as batch_op:
        batch_op.drop_index(f'ix_{table}_{old}')
        batch_op.alter_column(old, new_column_name=new)
    # Outside the batch: SQLite's table copy cannot index a column it renames.
    op.create_index(f'ix_{table}_{new}', table, [new], unique=False)


def upgrade() -> None:
    """Upgrade schema."""
    for table, old, new in RENAMES:
        _rename(table, old, new)


def downgrade() -> None:
    """Downgrade schema."""
    for table, old, new in reversed(RENAMES):
        _rename(table, new, old)
