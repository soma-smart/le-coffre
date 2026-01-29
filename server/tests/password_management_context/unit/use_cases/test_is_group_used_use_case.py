import pytest
from uuid import UUID

from password_management_context.application.use_cases import IsGroupUsedUseCase
from password_management_context.application.commands import IsGroupUsedCommand
from tests.password_management_context.unit.fakes import (
    FakePasswordPermissionsRepository,
)


@pytest.fixture
def use_case(password_permissions_repository):
    return IsGroupUsedUseCase(password_permissions_repository)


def test_should_return_true_when_group_has_passwords(
    use_case: IsGroupUsedUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    # Arrange
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    
    password_permissions_repository.set_owner(group_id, password_id)
    
    command = IsGroupUsedCommand(group_id=group_id)
    
    # Act
    result = use_case.execute(command)
    
    # Assert
    assert result is True


def test_should_return_false_when_group_has_no_passwords(
    use_case: IsGroupUsedUseCase,
):
    # Arrange
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    command = IsGroupUsedCommand(group_id=group_id)
    
    # Act
    result = use_case.execute(command)
    
    # Assert
    assert result is False


def test_should_return_false_when_group_does_not_exist(
    use_case: IsGroupUsedUseCase,
):
    # Arrange
    non_existent_group_id = UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e9")
    command = IsGroupUsedCommand(group_id=non_existent_group_id)
    
    # Act
    result = use_case.execute(command)
    
    # Assert
    assert result is False
