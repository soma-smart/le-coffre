import pytest
from uuid import UUID

from rights_access_context.application.use_cases import (
    SetOwnerAccessUseCase,
)
from ..fakes import FakeRightsRepository

# Test data constants
USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
RESOURCE_ID = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")


@pytest.fixture()
def use_case(rights_repository: FakeRightsRepository):
    return SetOwnerAccessUseCase(rights_repository)


def test_set_owner_access(
    use_case: SetOwnerAccessUseCase, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    use_case.execute(user_id, resource_id)

    assert rights_repository.is_owner(user_id, resource_id) is True


def test_given_not_owner_should_not_grant_access(
    use_case: SetOwnerAccessUseCase, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    assert rights_repository.is_owner(user_id, resource_id) is False
