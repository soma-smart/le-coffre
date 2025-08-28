import pytest

from rights_access_context.adapters.primary import (
    AccessControllerAdapter,
)
from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    GrantAccessUseCase,
)
from .mocks import FakeRightsRepository


@pytest.fixture()
def rights_repository():
    return FakeRightsRepository()


@pytest.fixture()
def access_controller(rights_repository: FakeRightsRepository):
    check_use_case = CheckAccessUseCase(rights_repository)
    grant_use_case = GrantAccessUseCase(rights_repository)
    return AccessControllerAdapter(check_use_case, grant_use_case)
