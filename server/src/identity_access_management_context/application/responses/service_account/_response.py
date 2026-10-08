from collections.abc import Hashable
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ItemResponse[IdT: Hashable]:
    """Response with an identified item."""

    id: IdT


@dataclass(frozen=True)
class ListResponse[ItemT: ItemResponse]:
    """Response with a sequence of identified items."""

    items: tuple[ItemT, ...]


@dataclass(frozen=True, kw_only=True)
class ServiceAccountResponse: ...


@dataclass(frozen=True, kw_only=True)
class ServiceAccountItemResponse(ServiceAccountResponse, ItemResponse[UUID]): ...
