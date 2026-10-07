"""Shared SQL infrastructure for repositories."""

from .prefixed_table import PrefixedTable
from .sql_base_repository import SQLBaseRepository

__all__ = ["PrefixedTable", "SQLBaseRepository"]
