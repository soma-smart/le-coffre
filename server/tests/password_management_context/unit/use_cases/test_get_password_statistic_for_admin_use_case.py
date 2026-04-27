from uuid import UUID

import pytest

from password_management_context.application.commands import GetPasswordStatisticForAdminCommand
from password_management_context.application.use_cases import GetPasswordStatisticForAdminUseCase
from password_management_context.domain.entities import Password
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE

from ..fakes import FakePasswordRepository


@pytest.fixture
def use_case(password_repository: FakePasswordRepository):
    return GetPasswordStatisticForAdminUseCase(password_repository)


@pytest.fixture
def admin_user():
    return AuthenticatedUser(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        roles=[ADMIN_ROLE],
    )


@pytest.fixture
def non_admin_user():
    return AuthenticatedUser(
        user_id=UUID("22222222-2222-2222-2222-222222222222"),
        roles=[],
    )


def test_given_admin_when_no_passwords_should_return_zero(
    use_case: GetPasswordStatisticForAdminUseCase,
    admin_user: AuthenticatedUser,
):
    command = GetPasswordStatisticForAdminCommand(requesting_user=admin_user)
    result = use_case.execute(command)

    assert result.password_count == 0


def test_given_admin_when_passwords_exist_should_return_correct_count(
    use_case: GetPasswordStatisticForAdminUseCase,
    password_repository: FakePasswordRepository,
    admin_user: AuthenticatedUser,
):
    password_repository.save(
        Password(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            name="Password 1",
            encrypted_value="encrypted1",
            folder="root",
        )
    )
    password_repository.save(
        Password(
            id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            name="Password 2",
            encrypted_value="encrypted2",
            folder="root",
        )
    )

    command = GetPasswordStatisticForAdminCommand(requesting_user=admin_user)
    result = use_case.execute(command)

    assert result.password_count == 2


def test_given_non_admin_user_when_getting_password_statistics_should_raise_not_admin_error(
    use_case: GetPasswordStatisticForAdminUseCase,
    non_admin_user: AuthenticatedUser,
):
    command = GetPasswordStatisticForAdminCommand(requesting_user=non_admin_user)

    with pytest.raises(NotAdminError):
        use_case.execute(command)
