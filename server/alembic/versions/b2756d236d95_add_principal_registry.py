"""add principal registry

Moves users and service accounts into a principal registry (`iam__principal`)
plus one details table per kind. Every id keeps its value, so nothing that
refers to a user or a service account needs touching.

Revision ID: b2756d236d95
Revises: 6f3f296a75c9
Create Date: 2026-10-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b2756d236d95'
down_revision: Union[str, Sequence[str], None] = '6f3f296a75c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('iam__principal',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.Enum('user', 'service_account', name='principal_kind', native_enum=False, create_constraint=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('iam__principal__user',
    sa.Column('principal_id', sa.Uuid(), nullable=False),
    sa.Column('username', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('roles', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('current_refresh_token_jti', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('session_invalid_before', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['principal_id'], ['iam__principal.id']),
    sa.PrimaryKeyConstraint('principal_id')
    )
    op.create_table('iam__principal__service_account',
    sa.Column('principal_id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['principal_id'], ['iam__principal.id']),
    sa.PrimaryKeyConstraint('principal_id')
    )
    op.create_index(op.f('ix_iam__principal__service_account_group_id'), 'iam__principal__service_account', ['group_id'], unique=False)
    op.create_index(op.f('ix_iam__principal__service_account_revoked_at'), 'iam__principal__service_account', ['revoked_at'], unique=False)
    op.create_index(op.f('ix_iam__principal__service_account_token_hash'), 'iam__principal__service_account', ['token_hash'], unique=True)

    # Ids are copied as they are: every other table refers to principals by them.
    op.execute(sa.text("""INSERT INTO iam__principal (id, kind) SELECT id, 'user' FROM "User\""""))
    op.execute(sa.text("""INSERT INTO iam__principal (id, kind) SELECT id, 'service_account' FROM "ServiceAccount\""""))
    # User.password_hash is left behind: passwords live in UserPassword, and nothing reads that column.
    op.execute(sa.text("""
        INSERT INTO iam__principal__user
            (principal_id, username, email, name, roles, current_refresh_token_jti, session_invalid_before)
        SELECT id, username, email, name, roles, current_refresh_token_jti, session_invalid_before FROM "User"
    """))
    op.execute(sa.text("""
        INSERT INTO iam__principal__service_account (principal_id, group_id, name, token_hash, revoked_at)
        SELECT id, group_id, name, token_hash, revoked_at FROM "ServiceAccount"
    """))

    op.drop_index(op.f('ix_ServiceAccount_token_hash'), table_name='ServiceAccount')
    op.drop_index(op.f('ix_ServiceAccount_revoked_at'), table_name='ServiceAccount')
    op.drop_index(op.f('ix_ServiceAccount_id'), table_name='ServiceAccount')
    op.drop_index(op.f('ix_ServiceAccount_group_id'), table_name='ServiceAccount')
    op.drop_table('ServiceAccount')
    op.drop_index(op.f('ix_User_id'), table_name='User')
    op.drop_table('User')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('User',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('username', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('roles', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('password_hash', sa.LargeBinary(), nullable=True),
    sa.Column('current_refresh_token_jti', sa.String(), nullable=True),
    sa.Column('session_invalid_before', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_User_id'), 'User', ['id'], unique=False)
    op.create_table('ServiceAccount',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ServiceAccount_group_id'), 'ServiceAccount', ['group_id'], unique=False)
    op.create_index(op.f('ix_ServiceAccount_id'), 'ServiceAccount', ['id'], unique=False)
    op.create_index(op.f('ix_ServiceAccount_revoked_at'), 'ServiceAccount', ['revoked_at'], unique=False)
    op.create_index(op.f('ix_ServiceAccount_token_hash'), 'ServiceAccount', ['token_hash'], unique=True)

    op.execute(sa.text("""
        INSERT INTO "User" (id, username, email, name, roles, current_refresh_token_jti, session_invalid_before)
        SELECT principal_id, username, email, name, roles, current_refresh_token_jti, session_invalid_before
        FROM iam__principal__user
    """))
    op.execute(sa.text("""
        INSERT INTO "ServiceAccount" (id, group_id, name, token_hash, revoked_at)
        SELECT principal_id, group_id, name, token_hash, revoked_at FROM iam__principal__service_account
    """))

    op.drop_index(op.f('ix_iam__principal__service_account_token_hash'), table_name='iam__principal__service_account')
    op.drop_index(op.f('ix_iam__principal__service_account_revoked_at'), table_name='iam__principal__service_account')
    op.drop_index(op.f('ix_iam__principal__service_account_group_id'), table_name='iam__principal__service_account')
    op.drop_table('iam__principal__service_account')
    op.drop_table('iam__principal__user')
    op.drop_table('iam__principal')
