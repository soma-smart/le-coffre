from uuid import UUID
import pytest
from rights_access_context.application.use_cases import (
    ShareAccessUseCase,
)
from ..mocks import FakeRightsRepository
from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.domain.exceptions import PermissionDeniedError


@pytest.fixture()
def use_case(rights_repository: FakeRightsRepository):
    return ShareAccessUseCase(rights_repository)


def test_when_sharing_owned_resource_should_grant_access(
    use_case: ShareAccessUseCase, rights_repository: FakeRightsRepository
):
    # Arrange
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    # Act
    rights_repository.add_permission(owner_id, resource_id)
    use_case.execute(ShareResourceCommand(owner_id, user_id, resource_id))

    # Assert
    assert rights_repository.has_permission(user_id, resource_id) is True


def test_when_sharing_not_owned_resource_should_fail(
    use_case: ShareAccessUseCase, rights_repository: FakeRightsRepository
):
    # Arrange
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e8")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    # Act
    with pytest.raises(PermissionDeniedError):
        use_case.execute(ShareResourceCommand(owner_id, user_id, resource_id))

    # Assert
    assert rights_repository.has_permission(user_id, resource_id) is False
