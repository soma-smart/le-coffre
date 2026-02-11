import pytest
from datetime import datetime

from vault_management_context.application.commands import ClearPendingSharesCommand
from vault_management_context.application.use_cases import ClearPendingSharesUseCase
from vault_management_context.domain.entities import Share
from ..fakes import FakeShareRepository


@pytest.fixture()
def use_case(share_repository: FakeShareRepository):
    return ClearPendingSharesUseCase(share_repository)


def test_given_pending_shares_when_clearing_should_remove_all_shares(
    use_case: ClearPendingSharesUseCase,
    share_repository: FakeShareRepository,
):
    # Arrange
    share1 = Share("0:abc123")
    share2 = Share("1:def456")
    share_repository.add([share1, share2])

    assert len(share_repository.get_all()) == 2

    command = ClearPendingSharesCommand()

    # Act
    use_case.execute(command)

    # Assert
    assert len(share_repository.get_all()) == 0


def test_given_no_pending_shares_when_clearing_should_not_raise_error(
    use_case: ClearPendingSharesUseCase,
    share_repository: FakeShareRepository,
):
    # Arrange
    assert len(share_repository.get_all()) == 0

    command = ClearPendingSharesCommand()

    # Act - should not raise any error
    use_case.execute(command)

    # Assert
    assert len(share_repository.get_all()) == 0


def test_given_pending_shares_with_timestamp_when_clearing_should_clear_timestamp(
    use_case: ClearPendingSharesUseCase,
    share_repository: FakeShareRepository,
):
    # Arrange
    share1 = Share("0:abc123")
    share_repository.add([share1])

    # Verify timestamp was set
    timestamp_before = share_repository.get_last_share_timestamp()
    assert timestamp_before is not None
    assert isinstance(timestamp_before, datetime)

    command = ClearPendingSharesCommand()

    # Act
    use_case.execute(command)

    # Assert
    assert share_repository.get_last_share_timestamp() is None
