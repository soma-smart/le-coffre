from typing import Any, ClassVar

from sqlalchemy.orm import declared_attr
from sqlmodel import SQLModel


class PrefixedTable(SQLModel):
    """Base for tables named by the ``__table_suffix__`` of each class in their lineage."""

    __table_suffix__: ClassVar[str]
    __table_name_parts__: ClassVar[tuple[str, ...]] = ()
    __table_part_sep__: ClassVar[str] = "__"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if "__table_suffix__" in cls.__dict__:
            cls.__table_name_parts__ = (*cls.__table_name_parts__, cls.__table_suffix__)
        super().__init_subclass__(**kwargs)

    @declared_attr  # type: ignore[misc]
    def __tablename__(cls) -> str:
        return cls.__table_part_sep__.join(cls.__table_name_parts__)
