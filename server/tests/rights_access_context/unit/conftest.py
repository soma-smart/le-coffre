import pytest

from rights_access_context.adapters.primary import (
    AccessControllerAdapter,
)
from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    SetOwnerAccessUseCase,
    GetOwnerAccessUseCase
)
from .fakes import FakeRightsRepository, FakeUserManagementGateway


@pytest.fixture()
def rights_repository():
    return FakeRightsRepository()


@pytest.fixture()
def user_management_gateway():
    return FakeUserManagementGateway()


@pytest.fixture()
def access_controller(rights_repository: FakeRightsRepository):
    check_use_case = CheckAccessUseCase(rights_repository)
    set_owner_use_case = SetOwnerAccessUseCase(rights_repository)
    get_owner_use_case = GetOwnerAccessUseCase(rights_repository)
    return AccessControllerAdapter(check_use_case, set_owner_use_case, get_owner_use_case)
