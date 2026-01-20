from .model.password import PasswordTable, create_password_table
from .model.permissions import (
    PermissionsTable,
    OwnershipTable,
    create_permissions_tables,
)

from .sql_password_permissions_repository import SqlPasswordPermissionsRepository
from .sql_password_repository import SqlPasswordRepository


def create_tables(engine):
    create_password_table(engine)
    create_permissions_tables(engine)
