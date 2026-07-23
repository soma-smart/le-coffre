"""Add revoked tokens and user session state

Revision ID: f1a2b3c4d5e6
Revises: 443d92366c2b
Create Date: 2026-07-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "443d92366c2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("User", sa.Column("current_refresh_token_jti", sa.String(), nullable=True))
    op.add_column("User", sa.Column("session_invalid_before", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "AuthSession",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("current_refresh_token_jti", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_AuthSession_id"), "AuthSession", ["id"], unique=False)
    op.create_index(op.f("ix_AuthSession_user_id"), "AuthSession", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_AuthSession_current_refresh_token_jti"),
        "AuthSession",
        ["current_refresh_token_jti"],
        unique=True,
    )
    op.create_index(op.f("ix_AuthSession_invalidated_at"), "AuthSession", ["invalidated_at"], unique=False)

    op.create_table(
        "RevokedToken",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("token_type", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_RevokedToken_id"), "RevokedToken", ["id"], unique=False)
    op.create_index(op.f("ix_RevokedToken_jti"), "RevokedToken", ["jti"], unique=True)
    op.create_index(op.f("ix_RevokedToken_user_id"), "RevokedToken", ["user_id"], unique=False)
    op.create_index(op.f("ix_RevokedToken_expires_at"), "RevokedToken", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_AuthSession_invalidated_at"), table_name="AuthSession")
    op.drop_index(op.f("ix_AuthSession_current_refresh_token_jti"), table_name="AuthSession")
    op.drop_index(op.f("ix_AuthSession_user_id"), table_name="AuthSession")
    op.drop_index(op.f("ix_AuthSession_id"), table_name="AuthSession")
    op.drop_table("AuthSession")

    op.drop_index(op.f("ix_RevokedToken_expires_at"), table_name="RevokedToken")
    op.drop_index(op.f("ix_RevokedToken_user_id"), table_name="RevokedToken")
    op.drop_index(op.f("ix_RevokedToken_jti"), table_name="RevokedToken")
    op.drop_index(op.f("ix_RevokedToken_id"), table_name="RevokedToken")
    op.drop_table("RevokedToken")

    op.drop_column("User", "session_invalid_before")
    op.drop_column("User", "current_refresh_token_jti")
