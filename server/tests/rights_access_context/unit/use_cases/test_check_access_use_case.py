import pytest
from uuid import UUID

from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
)
from ..mocks import FakeRightsRepository


@pytest.fixture()
def use_case(rights_repository: FakeRightsRepository):
    return CheckAccessUseCase(rights_repository)


def test_given_owned_resource_when_reading_should_grant_access(
    use_case: CheckAccessUseCase, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    rights_repository.grant_access(user_id, resource_id)

    result = use_case.execute(user_id, resource_id)

    assert result.granted is True


def test_given_not_owned_resource_when_reading_should_deny_access(
    use_case: CheckAccessUseCase,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    result = use_case.execute(user_id, resource_id)

    assert result.granted is False
