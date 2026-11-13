"""revoke service accounts of deleted groups

Deleting a user used to delete their personal group, and the shared groups they
alone owned, without revoking the service accounts of those groups: their tokens
kept authenticating, and with the group gone nobody could see the accounts to
revoke them. The application now revokes them first. Accounts orphaned before
that are revoked here, exactly as a revocation does it: token records deleted,
account row kept with its revocation time.

No audit event is written: there is no actor to credit.

Revision ID: 9c4e1a7b3d52
Revises: f2c8a61d4b07
Create Date: 2026-11-03 10:00:00.000000

"""
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4e1a7b3d52'
down_revision: Union[str, Sequence[str], None] = 'f2c8a61d4b07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORPHANED_ACCOUNTS = """
    SELECT principal_id FROM iam__principal__service_account
    WHERE revoked_at IS NULL AND group_id NOT IN (SELECT id FROM "Group")
"""

ORPHANED_TOKEN_CREDENTIALS = f"""
    SELECT id FROM iam__credential WHERE kind = 'token' AND principal_id IN ({ORPHANED_ACCOUNTS})
"""


def upgrade() -> None:
    """Upgrade schema."""
    # Tokens first, details before the registry: the cascade does not run where
    # foreign keys are not enforced.
    op.execute(sa.text(f"DELETE FROM iam__credential__token WHERE credential_id IN ({ORPHANED_TOKEN_CREDENTIALS})"))
    op.execute(sa.text(f"DELETE FROM iam__credential WHERE id IN ({ORPHANED_TOKEN_CREDENTIALS})"))
    op.execute(
        sa.text(
            """
            UPDATE iam__principal__service_account SET revoked_at = :now
            WHERE revoked_at IS NULL AND group_id NOT IN (SELECT id FROM "Group")
            """
        ).bindparams(now=datetime.now(UTC).replace(tzinfo=None))
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Nothing to restore: the deleted tokens belonged to accounts nobody could
    # manage any more, and giving them back would reopen the hole.
