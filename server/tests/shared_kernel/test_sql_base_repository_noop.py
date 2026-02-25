import pytest
from unittest.mock import MagicMock
from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository


@pytest.fixture
def repo():
    session = MagicMock()
    return SQLBaseRepository(session)


def test_operations_are_noop_without_provider(repo):
    """commit() and commit_and_refresh() must work with the real no-op tracer."""
    obj = MagicMock()
    repo.commit()
    repo._session.commit.assert_called_once()

    repo._session.reset_mock()
    repo.commit_and_refresh(obj)
    repo._session.commit.assert_called_once()
    repo._session.refresh.assert_called_once_with(obj)
