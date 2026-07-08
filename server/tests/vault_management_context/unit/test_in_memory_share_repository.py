from vault_management_context.adapters.secondary.in_memory_share_repository import (
    MAX_PENDING_SHARES,
    InMemoryShareRepository,
)
from vault_management_context.domain.entities import Share


def test_should_cap_pending_shares_to_bound_memory():
    repo = InMemoryShareRepository()

    repo.add([Share(f"{i}:x") for i in range(MAX_PENDING_SHARES + 25)])

    assert len(repo.get_all()) == MAX_PENDING_SHARES


def test_should_append_without_deduplicating():
    # The store is a dumb sink: deduplication is the use case's responsibility.
    repo = InMemoryShareRepository()

    repo.add([Share("0:a"), Share("0:a")])

    assert len(repo.get_all()) == 2
