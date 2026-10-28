"""move extension tokens to token credentials

Every extension token still usable becomes a token credential record of its
user: same id and same hash, so paired extensions keep working. Revoked and
expired ones are left behind with their table: their history is in the audit
trail. Each moved record carries the inactivity limit configured today.

Revision ID: e41b6f0c2d93
Revises: a237709960ce
Create Date: 2026-10-29 11:00:00.000000

"""
import os
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e41b6f0c2d93'
down_revision: Union[str, Sequence[str], None] = 'a237709960ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same setting, and same default, as config.get_extension_token_inactivity_seconds.
INACTIVITY_SECONDS = int(os.environ.get("EXTENSION_TOKEN_INACTIVITY_DAYS", "14")) * 86400

# What a moved record looked like as an extension token: read-only, the only
# kind of token credential the extension ever issued.
EXTENSION_TOKEN_CREDENTIALS = """
    SELECT c.id FROM iam__credential c
    JOIN iam__credential__token t ON t.credential_id = c.id
    WHERE c.kind = 'token' AND t.read_only
"""


def upgrade() -> None:
    """Upgrade schema."""
    now = datetime.now(UTC).replace(tzinfo=None)
    usable = """
        FROM "ExtensionToken" e
        JOIN iam__principal p ON p.id = e.user_id
        WHERE e.revoked_at IS NULL AND e.expires_at > :now
    """
    op.execute(
        sa.text(f"INSERT INTO iam__credential (id, kind, principal_id) SELECT e.id, 'token', e.user_id {usable}")
        .bindparams(now=now)
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO iam__credential__token
                (credential_id, token_hash, read_only, label, expires_at, last_used_at, max_idle_seconds)
            SELECT e.id, e.token_hash, :read_only, e.device_name, e.expires_at,
                   COALESCE(e.last_used_at, e.created_at), :max_idle_seconds
            {usable}
            """
        ).bindparams(now=now, read_only=True, max_idle_seconds=INACTIVITY_SECONDS)
    )

    op.drop_index(op.f('ix_ExtensionToken_user_id'), table_name='ExtensionToken')
    op.drop_index(op.f('ix_ExtensionToken_token_hash'), table_name='ExtensionToken')
    op.drop_index(op.f('ix_ExtensionToken_revoked_at'), table_name='ExtensionToken')
    op.drop_index(op.f('ix_ExtensionToken_id'), table_name='ExtensionToken')
    op.drop_index(op.f('ix_ExtensionToken_expires_at'), table_name='ExtensionToken')
    op.drop_table('ExtensionToken')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('ExtensionToken',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('device_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('created_from_ip', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ExtensionToken_expires_at'), 'ExtensionToken', ['expires_at'], unique=False)
    op.create_index(op.f('ix_ExtensionToken_id'), 'ExtensionToken', ['id'], unique=False)
    op.create_index(op.f('ix_ExtensionToken_revoked_at'), 'ExtensionToken', ['revoked_at'], unique=False)
    op.create_index(op.f('ix_ExtensionToken_token_hash'), 'ExtensionToken', ['token_hash'], unique=True)
    op.create_index(op.f('ix_ExtensionToken_user_id'), 'ExtensionToken', ['user_id'], unique=False)

    # The creation date is gone: the last use, set at issuance, stands in for it.
    op.execute(
        sa.text(
            """
            INSERT INTO "ExtensionToken" (id, user_id, token_hash, device_name, created_at, expires_at, last_used_at)
            SELECT c.id, c.principal_id, t.token_hash, COALESCE(t.label, 'Browser extension'),
                   COALESCE(t.last_used_at, t.expires_at), t.expires_at, t.last_used_at
            FROM iam__credential c
            JOIN iam__credential__token t ON t.credential_id = c.id
            WHERE c.kind = 'token' AND t.read_only AND t.expires_at IS NOT NULL
            """
        )
    )
    # Details first: the cascade does not run where foreign keys are not enforced.
    op.execute(sa.text(f"DELETE FROM iam__credential__token WHERE credential_id IN ({EXTENSION_TOKEN_CREDENTIALS})"))
    op.execute(sa.text("DELETE FROM iam__credential WHERE kind = 'token' AND id NOT IN (SELECT credential_id FROM iam__credential__token)"))
