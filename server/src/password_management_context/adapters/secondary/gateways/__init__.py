from .in_memory_password_repository import InMemoryPasswordRepository

from .sql.model.password import create_password_table
from .sql.sql_password_repository import SqlPasswordRepository

__all__ = ["InMemoryPasswordRepository"]

def create_tables(engine):
    create_password_table(engine)
