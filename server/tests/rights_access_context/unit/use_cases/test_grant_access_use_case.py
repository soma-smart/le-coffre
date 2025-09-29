import pytest
from uuid import UUID

from rights_access_context.application.use_cases import (
    GrantAccessUseCase,
)
from ..mocks import FakeRightsRepository


@pytest.fixture()
def use_case(rights_repository: FakeRightsRepository):
    return GrantAccessUseCase(rights_repository)


def test_should_grant_access_to_user_for_resource(
    use_case: GrantAccessUseCase, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    use_case.execute(user_id, resource_id)

    assert rights_repository.has_permission(user_id, resource_id) is True
