from identity_access_management_context.adapters.secondary.sql import (
    PrincipalTable,
    ServiceAccountPrincipalTable,
    UserPrincipalTable,
)
from shared_kernel.adapters.secondary.sql import PrefixedTable


class ContextTable(PrefixedTable):
    __table_suffix__ = "ctx"


class NestedTable(ContextTable):
    __table_suffix__ = "nested"


class LeafTable(NestedTable):
    __table_suffix__ = "leaf"


class UnsuffixedTable(NestedTable):
    pass


def test_tablename_joins_each_ancestor_suffix():
    assert LeafTable.__table_name_parts__ == ("ctx", "nested", "leaf")
    assert LeafTable.__tablename__ == "ctx__nested__leaf"


def test_subclass_without_suffix_keeps_parent_parts():
    assert UnsuffixedTable.__table_name_parts__ == ("ctx", "nested")


def test_iam_table_names():
    assert PrincipalTable.__tablename__ == "iam__principal"
    assert UserPrincipalTable.__tablename__ == "iam__principal__user"
    assert ServiceAccountPrincipalTable.__tablename__ == "iam__principal__service_account"
