"""delete token credentials of revoked service accounts

Revoking a service account now deletes its token credential records, so that
authenticators never have to know about revocation. Accounts revoked before
that still hold theirs: they are deleted here.

Revision ID: 528c0676a893
Revises: c2fe6004a6d0
Create Date: 2026-10-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '528c0676a893'
down_revision: Union[str, Sequence[str], None] = 'c2fe6004a6d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REVOKED_TOKEN_CREDENTIALS = """
    SELECT c.id FROM iam__credential c
    JOIN iam__principal__service_account sa ON sa.principal_id = c.principal_id
    WHERE c.kind = 'token' AND sa.revoked_at IS NOT NULL
"""


def upgrade() -> None:
    """Upgrade schema."""
    # Details first: the cascade does not run where foreign keys are not enforced.
    op.execute(sa.text(
        f"DELETE FROM iam__credential__token WHERE credential_id IN ({REVOKED_TOKEN_CREDENTIALS})"
    ))
    op.execute(sa.text(f"DELETE FROM iam__credential WHERE id IN ({REVOKED_TOKEN_CREDENTIALS})"))


def downgrade() -> None:
    """Downgrade schema."""
    # Nothing to restore: only hashes were deleted, and a revoked account's token
    # was refused before this revision too.
