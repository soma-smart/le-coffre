from unittest.mock import MagicMock, patch
from uuid import uuid4

from password_management_context.application.commands import CheckAccessCommand
from password_management_context.application.use_cases.access.check_access_use_case import CheckAccessUseCase
from password_management_context.domain.value_objects import PasswordGroupAccess, PasswordPermission
from shared_kernel.domain.value_objects import Granted
from tests.shared_kernel.fakes.fake_time_gateway import FakeTimeGateway

_COUNTER_PATH = (
    "password_management_context.application.use_cases.access.check_access_use_case.access_check_not_found_counter"
)


_GROUP_ID = uuid4()


def _make_use_case(is_owner=False, has_access=False):
    repo = MagicMock()
    if is_owner:
        repo.list_all_permissions_for.return_value = {_GROUP_ID: PasswordGroupAccess(is_owner=True)}
    elif has_access:
        repo.list_all_permissions_for.return_value = {
            _GROUP_ID: PasswordGroupAccess(is_owner=False, permissions={PasswordPermission.READ})
        }
    else:
        repo.list_all_permissions_for.return_value = {}
    return CheckAccessUseCase(repo, FakeTimeGateway())


def _make_command():
    return CheckAccessCommand(user_id=_GROUP_ID, resource_id=uuid4())


def test_check_access_not_found_increments_counter():
    """When access returns NOT_FOUND, the access.check.not_found counter must be incremented."""
    mock_counter = MagicMock()
    use_case = _make_use_case(is_owner=False, has_access=False)

    with patch(_COUNTER_PATH, mock_counter):
        result = use_case.execute(_make_command())

    mock_counter.add.assert_called_once_with(1)
    assert result.granted == Granted.NOT_FOUND


def test_check_access_granted_does_not_increment_counter():
    """When access is granted, the counter must not be incremented."""
    mock_counter = MagicMock()
    use_case = _make_use_case(is_owner=False, has_access=True)

    with patch(_COUNTER_PATH, mock_counter):
        result = use_case.execute(_make_command())

    mock_counter.add.assert_not_called()
    assert result.granted == Granted.ACCESS


def test_check_access_owner_does_not_increment_counter():
    """When user is owner, the counter must not be incremented."""
    mock_counter = MagicMock()
    use_case = _make_use_case(is_owner=True)

    with patch(_COUNTER_PATH, mock_counter):
        result = use_case.execute(_make_command())

    mock_counter.add.assert_not_called()
    assert result.granted == Granted.ACCESS
