import pytest
from uuid import UUID

from rights_access_context.adapters.primary import AccessControllerAdapter
from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    GrantAccessUseCase,
)
from ...mocks import FakeRightsRepository


@pytest.fixture()
def adapter(rights_repository: FakeRightsRepository):
    check_use_case = CheckAccessUseCase(rights_repository)
    grant_use_case = GrantAccessUseCase(rights_repository)
    return AccessControllerAdapter(check_use_case, grant_use_case)


def test_should_check_access_through_check_use_case(
    adapter: AccessControllerAdapter, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    rights_repository.grant_access(user_id, resource_id)

    result = adapter.check_access(user_id, resource_id)

    assert result is True


def test_should_grant_access_through_grant_use_case(
    adapter: AccessControllerAdapter, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    adapter.grant_access(user_id, resource_id)

    assert rights_repository.has_access(user_id, resource_id) is True
