from uuid import UUID

import pytest

from identity_access_management_context.application.commands import GetStatisticForAdminCommand
from identity_access_management_context.application.use_cases import GetStatisticForAdminUseCase
from identity_access_management_context.domain.entities import Group, PersonalGroup, User
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE

from ..fakes import FakeGroupRepository, FakeUserRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
):
    return GetStatisticForAdminUseCase(user_repository, group_repository)


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


def test_given_admin_when_no_users_and_no_groups_should_return_zeros(
    use_case: GetStatisticForAdminUseCase,
    admin_user: AuthenticatedUser,
):
    command = GetStatisticForAdminCommand(requesting_user=admin_user)
    result = use_case.execute(command)

    assert result.user_count == 0
    assert result.group_count == 0


def test_given_admin_when_users_exist_should_return_correct_user_count(
    use_case: GetStatisticForAdminUseCase,
    user_repository: FakeUserRepository,
    admin_user: AuthenticatedUser,
):
    user_repository.save(
        User(id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), username="user1", email="u1@test.com", name="User 1")
    )
    user_repository.save(
        User(id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), username="user2", email="u2@test.com", name="User 2")
    )

    command = GetStatisticForAdminCommand(requesting_user=admin_user)
    result = use_case.execute(command)

    assert result.user_count == 2


def test_given_admin_when_non_personal_groups_exist_should_return_correct_group_count(
    use_case: GetStatisticForAdminUseCase,
    group_repository: FakeGroupRepository,
    admin_user: AuthenticatedUser,
):
    group_repository.save_group(
        Group(id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"), name="Team A", is_personal=False)
    )
    group_repository.save_group(
        Group(id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"), name="Team B", is_personal=False)
    )

    command = GetStatisticForAdminCommand(requesting_user=admin_user)
    result = use_case.execute(command)

    assert result.group_count == 2


def test_given_admin_when_personal_groups_exist_should_not_count_them(
    use_case: GetStatisticForAdminUseCase,
    group_repository: FakeGroupRepository,
    admin_user: AuthenticatedUser,
):
    group_repository.save_group(
        Group(id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"), name="Team A", is_personal=False)
    )
    group_repository.save_personal_group(
        PersonalGroup(
            id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            name="Personal",
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
        )
    )

    command = GetStatisticForAdminCommand(requesting_user=admin_user)
    result = use_case.execute(command)

    assert result.group_count == 1


def test_given_non_admin_user_when_getting_statistics_should_raise_not_admin_error(
    use_case: GetStatisticForAdminUseCase,
    non_admin_user: AuthenticatedUser,
):
    command = GetStatisticForAdminCommand(requesting_user=non_admin_user)

    with pytest.raises(NotAdminError):
        use_case.execute(command)
