from datetime import UTC, datetime
from uuid import UUID

import pytest

from password_management_context.application.commands import GetPasswordStatisticForAdminCommand
from password_management_context.application.use_cases import GetPasswordStatisticForAdminUseCase
from password_management_context.domain.entities import Password
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import FakeOneTimeLinkRepository, FakePasswordRepository

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=T0)


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    one_time_link_repository: FakeOneTimeLinkRepository,
    time_gateway: FakeTimeGateway,
):
    return GetPasswordStatisticForAdminUseCase(password_repository, one_time_link_repository, time_gateway)


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


def test_given_admin_should_report_total_and_active_one_time_link_counts(
    use_case: GetPasswordStatisticForAdminUseCase,
    one_time_link_repository: FakeOneTimeLinkRepository,
    admin_user: AuthenticatedUser,
):
    """The two numbers answer different questions: the total measures usage over
    time, the active count says how many anonymous read grants are open now."""
    from uuid import uuid4

    from password_management_context.domain.entities import OneTimeLink
    from password_management_context.domain.value_objects import (
        OneTimeLinkLifetime,
        OneTimeLinkToken,
    )

    def issue() -> OneTimeLink:
        link = OneTimeLink.create(
            password_id=uuid4(),
            created_by_user_id=uuid4(),
            token=OneTimeLinkToken.generate(),
            lifetime=OneTimeLinkLifetime.default(),
            now=T0,
        )
        one_time_link_repository.add(link)
        return link

    issue()
    one_time_link_repository.consume(issue().id, T0)
    one_time_link_repository.revoke(issue().id, T0)

    result = use_case.execute(GetPasswordStatisticForAdminCommand(requesting_user=admin_user))

    assert result.one_time_link_count == 3
    assert result.active_one_time_link_count == 1
