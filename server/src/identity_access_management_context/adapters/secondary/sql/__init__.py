from .model.group_model import GroupTable, create_group_table
from .model.group_member_model import GroupMemberTable, create_group_member_table
from .model.sso_configuration_model import (
    SsoConfigurationTable,
    create_sso_configuration_table,
)
from .sql_group_repository import SqlGroupRepository
from .sql_group_member_repository import SqlGroupMemberRepository
from .sql_user_repository import SqlUserRepository
from .sql_user_password_repository import SqlUserPasswordRepository
from .sql_sso_user_repository import SqlSsoUserRepository
from .sql_sso_configuration_repository import SqlSsoConfigurationRepository


def create_tables(engine):
    create_group_table(engine)
    create_group_member_table(engine)
    create_sso_configuration_table(engine)


__all__ = [
    "SqlGroupRepository",
    "SqlGroupMemberRepository",
    "SqlUserRepository",
    "SqlUserPasswordRepository",
    "SqlSsoUserRepository",
    "SqlSsoConfigurationRepository",
    "GroupTable",
    "GroupMemberTable",
    "SsoConfigurationTable",
    "create_tables",
]
