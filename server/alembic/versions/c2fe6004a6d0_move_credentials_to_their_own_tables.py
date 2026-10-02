"""move credentials to their own tables

Every stored verifier becomes a credential: a row in the credential registry
(`iam__credential`), naming its kind and the principal it proves, plus one
details table per kind. `UserPassword` -> `iam__credential__password`,
`SsoUser` -> `iam__credential__sso`, and the service-account token hash ->
`iam__credential__token`. The email and display-name copies
kept next to the SSO subject and the password are dropped, except the
password's email, which is what a user logs in with.

Revision ID: c2fe6004a6d0
Revises: b2756d236d95
Create Date: 2026-10-01 15:00:00.000000

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c2fe6004a6d0'
down_revision: Union[str, Sequence[str], None] = 'b2756d236d95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


credential = sa.table(
    'iam__credential',
    sa.column('id', sa.Uuid()),
    sa.column('kind', sa.String()),
    sa.column('principal_id', sa.Uuid()),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('iam__credential',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.Enum('password', 'token', 'sso', name='credential_kind', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('principal_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['principal_id'], ['iam__principal.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_iam__credential_principal_id'), 'iam__credential', ['principal_id'], unique=False)
    op.create_table('iam__credential__password',
    sa.Column('credential_id', sa.Uuid(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('password_hash', sa.LargeBinary(), nullable=False),
    sa.ForeignKeyConstraint(['credential_id'], ['iam__credential.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('credential_id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('iam__credential__sso',
    sa.Column('credential_id', sa.Uuid(), nullable=False),
    sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['credential_id'], ['iam__credential.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('credential_id'),
    sa.UniqueConstraint('provider', 'subject')
    )
    op.create_table('iam__credential__token',
    sa.Column('credential_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['credential_id'], ['iam__credential.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('credential_id')
    )
    op.create_index(op.f('ix_iam__credential__token_token_hash'), 'iam__credential__token', ['token_hash'], unique=True)

    bind = op.get_bind()
    principal_ids = set(bind.execute(sa.select(sa.column('id', sa.Uuid())).select_from(sa.table('iam__principal'))).scalars())

    def move(kind: str, source: sa.Select, details_table: str, *names: str) -> None:
        """Give each source row a registry row of this kind, and its details row."""
        details = sa.table(details_table, sa.column('credential_id', sa.Uuid()), *map(sa.column, names))
        for row in bind.execute(source).mappings():
            # A verifier whose principal is gone already fails every login; the
            # foreign key would refuse it, so it is left behind with its table.
            if row['principal_id'] not in principal_ids:
                continue
            credential_id = uuid4()
            bind.execute(credential.insert().values(id=credential_id, kind=kind, principal_id=row['principal_id']))
            bind.execute(details.insert().values(credential_id=credential_id, **{name: row[name] for name in names}))

    move(
        'password',
        sa.select(
            sa.column('id', sa.Uuid()).label('principal_id'), sa.column('email'), sa.column('password_hash')
        ).select_from(sa.table('UserPassword')),
        'iam__credential__password',
        'email', 'password_hash',
    )
    move(
        'sso',
        sa.select(
            sa.column('internal_user_id', sa.Uuid()).label('principal_id'),
            sa.column('sso_provider').label('provider'),
            sa.column('sso_user_id').label('subject'),
            sa.column('created_at', sa.DateTime()),
            sa.column('last_login', sa.DateTime()),
        ).select_from(sa.table('SsoUser')),
        'iam__credential__sso',
        'provider', 'subject', 'created_at', 'last_login',
    )
    move(
        'token',
        sa.select(sa.column('principal_id', sa.Uuid()), sa.column('token_hash')).select_from(
            sa.table('iam__principal__service_account')
        ),
        'iam__credential__token',
        'token_hash',
    )

    op.drop_index(op.f('ix_iam__principal__service_account_token_hash'), table_name='iam__principal__service_account')
    with op.batch_alter_table('iam__principal__service_account') as batch_op:
        batch_op.drop_column('token_hash')
    op.drop_index(op.f('ix_UserPassword_id'), table_name='UserPassword')
    op.drop_table('UserPassword')
    op.drop_index(op.f('ix_SsoUser_internal_user_id'), table_name='SsoUser')
    op.drop_table('SsoUser')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('SsoUser',
    sa.Column('internal_user_id', sa.Uuid(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('sso_user_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('sso_provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('internal_user_id')
    )
    op.create_index(op.f('ix_SsoUser_internal_user_id'), 'SsoUser', ['internal_user_id'], unique=False)
    op.create_table('UserPassword',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('password_hash', sa.LargeBinary(), nullable=False),
    sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_UserPassword_id'), 'UserPassword', ['id'], unique=False)

    # The dropped copies are rebuilt from the user, which is what the upgrade made authoritative.
    op.execute(sa.text("""
        INSERT INTO "UserPassword" (id, email, password_hash, display_name)
        SELECT c.principal_id, d.email, d.password_hash, u.name
        FROM iam__credential c
        JOIN iam__credential__password d ON d.credential_id = c.id
        JOIN iam__principal__user u ON u.principal_id = c.principal_id
    """))
    op.execute(sa.text("""
        INSERT INTO "SsoUser" (internal_user_id, email, display_name, sso_user_id, sso_provider, created_at, last_login)
        SELECT c.principal_id, u.email, u.name, d.subject, d.provider, d.created_at, d.last_login
        FROM iam__credential c
        JOIN iam__credential__sso d ON d.credential_id = c.id
        JOIN iam__principal__user u ON u.principal_id = c.principal_id
    """))

    with op.batch_alter_table('iam__principal__service_account') as batch_op:
        batch_op.add_column(sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.execute(sa.text("""
        UPDATE iam__principal__service_account SET token_hash = (
            SELECT d.token_hash
            FROM iam__credential c JOIN iam__credential__token d ON d.credential_id = c.id
            WHERE c.principal_id = iam__principal__service_account.principal_id
        )
    """))
    with op.batch_alter_table('iam__principal__service_account') as batch_op:
        batch_op.alter_column('token_hash', existing_type=sqlmodel.sql.sqltypes.AutoString(), nullable=False)
    op.create_index(op.f('ix_iam__principal__service_account_token_hash'), 'iam__principal__service_account', ['token_hash'], unique=True)

    op.drop_index(op.f('ix_iam__credential__token_token_hash'), table_name='iam__credential__token')
    op.drop_table('iam__credential__token')
    op.drop_table('iam__credential__sso')
    op.drop_table('iam__credential__password')
    op.drop_index(op.f('ix_iam__credential_principal_id'), table_name='iam__credential')
    op.drop_table('iam__credential')
