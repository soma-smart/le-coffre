from shared_kernel.adapters.secondary.sql import PrefixedTable


class IAMTable(PrefixedTable):
    """Base for identity & access management tables, named ``iam__<entity>``."""

    __table_suffix__ = "iam"
