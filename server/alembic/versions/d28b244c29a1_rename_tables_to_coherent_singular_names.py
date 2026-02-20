"""Rename tables to coherent singular names

Revision ID: d28b244c29a1
Revises: c3f8a912b047
Create Date: 2026-02-18 07:45:28.913357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd28b244c29a1'
down_revision: Union[str, Sequence[str], None] = 'c3f8a912b047'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename all tables to coherent singular names without Table suffix
    op.rename_table('GroupMemberTable', 'GroupMember')
    op.rename_table('GroupTable', 'Group')
    op.rename_table('OwnershipTable', 'Ownership')
    op.rename_table('PasswordTable', 'Password')
    op.rename_table('PermissionsTable', 'Permission')
    op.rename_table('SsoConfigurationTable', 'SsoConfiguration')
    op.rename_table('SsoUsersTable', 'SsoUser')
    op.rename_table('UserPasswordTable', 'UserPassword')
    op.rename_table('UserTable', 'User')
    # Rename vault-related tables with temp names to handle case-insensitivity
    op.rename_table('vault', '_temp_vault')
    op.rename_table('iam_events', '_temp_iam_events')
    op.rename_table('password_events', '_temp_password_events')
    op.rename_table('vault_events', '_temp_vault_events')
    # Now rename to final names
    op.rename_table('_temp_vault', 'Vault')
    op.rename_table('_temp_iam_events', 'IamEvent')
    op.rename_table('_temp_password_events', 'PasswordEvent')
    op.rename_table('_temp_vault_events', 'VaultEvent')
    
    # Rename indexes to match new table names
    # Group table indexes
    op.drop_index(op.f('ix_GroupTable_id'), table_name='Group')
    op.drop_index(op.f('ix_GroupTable_user_id'), table_name='Group')
    op.create_index(op.f('ix_Group_id'), 'Group', ['id'], unique=False)
    op.create_index(op.f('ix_Group_user_id'), 'Group', ['user_id'], unique=False)
    
    # GroupMember table indexes
    op.drop_index(op.f('ix_GroupMemberTable_group_id'), table_name='GroupMember')
    op.drop_index(op.f('ix_GroupMemberTable_user_id'), table_name='GroupMember')
    op.create_index(op.f('ix_GroupMember_group_id'), 'GroupMember', ['group_id'], unique=False)
    op.create_index(op.f('ix_GroupMember_user_id'), 'GroupMember', ['user_id'], unique=False)
    
    # Ownership table indexes
    op.drop_index(op.f('ix_OwnershipTable_id'), table_name='Ownership')
    op.create_index(op.f('ix_Ownership_id'), 'Ownership', ['id'], unique=False)
    
    # Password table indexes
    op.drop_index(op.f('ix_PasswordTable_id'), table_name='Password')
    op.create_index(op.f('ix_Password_id'), 'Password', ['id'], unique=False)
    
    # Permission table indexes
    op.drop_index(op.f('ix_PermissionsTable_id'), table_name='Permission')
    op.create_index(op.f('ix_Permission_id'), 'Permission', ['id'], unique=False)
    
    # SsoUser table indexes
    op.drop_index(op.f('ix_SsoUsersTable_internal_user_id'), table_name='SsoUser')
    op.create_index(op.f('ix_SsoUser_internal_user_id'), 'SsoUser', ['internal_user_id'], unique=False)
    
    # User table indexes
    op.drop_index(op.f('ix_UserTable_id'), table_name='User')
    op.create_index(op.f('ix_User_id'), 'User', ['id'], unique=False)
    
    # UserPassword table indexes
    op.drop_index(op.f('ix_UserPasswordTable_id'), table_name='UserPassword')
    op.create_index(op.f('ix_UserPassword_id'), 'UserPassword', ['id'], unique=False)
    
    # IamEvent table indexes (renamed from iam_events)
    op.drop_index(op.f('ix_iam_events_actor_user_id'), table_name='IamEvent')
    op.drop_index(op.f('ix_iam_events_event_type'), table_name='IamEvent')
    op.drop_index(op.f('ix_iam_events_occurred_on'), table_name='IamEvent')
    op.create_index(op.f('ix_IamEvent_actor_user_id'), 'IamEvent', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_IamEvent_event_type'), 'IamEvent', ['event_type'], unique=False)
    op.create_index(op.f('ix_IamEvent_occurred_on'), 'IamEvent', ['occurred_on'], unique=False)
    
    # PasswordEvent table indexes (renamed from password_events)
    op.drop_index(op.f('ix_password_events_actor_user_id'), table_name='PasswordEvent')
    op.drop_index(op.f('ix_password_events_event_type'), table_name='PasswordEvent')
    op.drop_index(op.f('ix_password_events_occurred_on'), table_name='PasswordEvent')
    op.drop_index(op.f('ix_password_events_password_id'), table_name='PasswordEvent')
    op.create_index(op.f('ix_PasswordEvent_actor_user_id'), 'PasswordEvent', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_PasswordEvent_event_type'), 'PasswordEvent', ['event_type'], unique=False)
    op.create_index(op.f('ix_PasswordEvent_occurred_on'), 'PasswordEvent', ['occurred_on'], unique=False)
    op.create_index(op.f('ix_PasswordEvent_password_id'), 'PasswordEvent', ['password_id'], unique=False)
    
    # VaultEvent table indexes (renamed from vault_events)
    op.drop_index(op.f('ix_vault_events_actor_user_id'), table_name='VaultEvent')
    op.drop_index(op.f('ix_vault_events_event_type'), table_name='VaultEvent')
    op.drop_index(op.f('ix_vault_events_occurred_on'), table_name='VaultEvent')
    op.create_index(op.f('ix_VaultEvent_actor_user_id'), 'VaultEvent', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_VaultEvent_event_type'), 'VaultEvent', ['event_type'], unique=False)
    op.create_index(op.f('ix_VaultEvent_occurred_on'), 'VaultEvent', ['occurred_on'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert index names back to original
    # VaultEvent indexes
    op.drop_index(op.f('ix_VaultEvent_occurred_on'), table_name='VaultEvent')
    op.drop_index(op.f('ix_VaultEvent_event_type'), table_name='VaultEvent')
    op.drop_index(op.f('ix_VaultEvent_actor_user_id'), table_name='VaultEvent')
    op.create_index(op.f('ix_vault_events_occurred_on'), 'VaultEvent', ['occurred_on'], unique=False)
    op.create_index(op.f('ix_vault_events_event_type'), 'VaultEvent', ['event_type'], unique=False)
    op.create_index(op.f('ix_vault_events_actor_user_id'), 'VaultEvent', ['actor_user_id'], unique=False)
    
    # PasswordEvent indexes
    op.drop_index(op.f('ix_PasswordEvent_password_id'), table_name='PasswordEvent')
    op.drop_index(op.f('ix_PasswordEvent_occurred_on'), table_name='PasswordEvent')
    op.drop_index(op.f('ix_PasswordEvent_event_type'), table_name='PasswordEvent')
    op.drop_index(op.f('ix_PasswordEvent_actor_user_id'), table_name='PasswordEvent')
    op.create_index(op.f('ix_password_events_password_id'), 'PasswordEvent', ['password_id'], unique=False)
    op.create_index(op.f('ix_password_events_occurred_on'), 'PasswordEvent', ['occurred_on'], unique=False)
    op.create_index(op.f('ix_password_events_event_type'), 'PasswordEvent', ['event_type'], unique=False)
    op.create_index(op.f('ix_password_events_actor_user_id'), 'PasswordEvent', ['actor_user_id'], unique=False)
    
    # IamEvent indexes
    op.drop_index(op.f('ix_IamEvent_occurred_on'), table_name='IamEvent')
    op.drop_index(op.f('ix_IamEvent_event_type'), table_name='IamEvent')
    op.drop_index(op.f('ix_IamEvent_actor_user_id'), table_name='IamEvent')
    op.create_index(op.f('ix_iam_events_occurred_on'), 'IamEvent', ['occurred_on'], unique=False)
    op.create_index(op.f('ix_iam_events_event_type'), 'IamEvent', ['event_type'], unique=False)
    op.create_index(op.f('ix_iam_events_actor_user_id'), 'IamEvent', ['actor_user_id'], unique=False)
    
    # UserPassword indexes
    op.drop_index(op.f('ix_UserPassword_id'), table_name='UserPassword')
    op.create_index(op.f('ix_UserPasswordTable_id'), 'UserPassword', ['id'], unique=False)
    
    # User indexes
    op.drop_index(op.f('ix_User_id'), table_name='User')
    op.create_index(op.f('ix_UserTable_id'), 'User', ['id'], unique=False)
    
    # SsoUser indexes
    op.drop_index(op.f('ix_SsoUser_internal_user_id'), table_name='SsoUser')
    op.create_index(op.f('ix_SsoUsersTable_internal_user_id'), 'SsoUser', ['internal_user_id'], unique=False)
    
    # Permission indexes
    op.drop_index(op.f('ix_Permission_id'), table_name='Permission')
    op.create_index(op.f('ix_PermissionsTable_id'), 'Permission', ['id'], unique=False)
    
    # Password indexes
    op.drop_index(op.f('ix_Password_id'), table_name='Password')
    op.create_index(op.f('ix_PasswordTable_id'), 'Password', ['id'], unique=False)
    
    # Ownership indexes
    op.drop_index(op.f('ix_Ownership_id'), table_name='Ownership')
    op.create_index(op.f('ix_OwnershipTable_id'), 'Ownership', ['id'], unique=False)
    
    # GroupMember indexes
    op.drop_index(op.f('ix_GroupMember_user_id'), table_name='GroupMember')
    op.drop_index(op.f('ix_GroupMember_group_id'), table_name='GroupMember')
    op.create_index(op.f('ix_GroupMemberTable_user_id'), 'GroupMember', ['user_id'], unique=False)
    op.create_index(op.f('ix_GroupMemberTable_group_id'), 'GroupMember', ['group_id'], unique=False)
    
    # Group indexes
    op.drop_index(op.f('ix_Group_user_id'), table_name='Group')
    op.drop_index(op.f('ix_Group_id'), table_name='Group')
    op.create_index(op.f('ix_GroupTable_user_id'), 'Group', ['user_id'], unique=False)
    op.create_index(op.f('ix_GroupTable_id'), 'Group', ['id'], unique=False)
    
    # Revert table names back to original names
    # Use temp names for case-sensitivity issues
    op.rename_table('VaultEvent', '_temp_vault_events')
    op.rename_table('PasswordEvent', '_temp_password_events')
    op.rename_table('IamEvent', '_temp_iam_events')
    op.rename_table('Vault', '_temp_vault')
    # Now rename to final lowercase names
    op.rename_table('_temp_vault_events', 'vault_events')
    op.rename_table('_temp_password_events', 'password_events')
    op.rename_table('_temp_iam_events', 'iam_events')
    op.rename_table('_temp_vault', 'vault')
    # Rename other tables
    op.rename_table('User', 'UserTable')
    op.rename_table('UserPassword', 'UserPasswordTable')
    op.rename_table('SsoUser', 'SsoUsersTable')
    op.rename_table('SsoConfiguration', 'SsoConfigurationTable')
    op.rename_table('Permission', 'PermissionsTable')
    op.rename_table('Password', 'PasswordTable')
    op.rename_table('Ownership', 'OwnershipTable')
    op.rename_table('Group', 'GroupTable')
    op.rename_table('GroupMember', 'GroupMemberTable')
