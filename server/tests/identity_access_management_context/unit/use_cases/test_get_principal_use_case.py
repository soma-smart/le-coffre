from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import GetPrincipalCommand
from identity_access_management_context.application.responses import GetPrincipalResponse
from identity_access_management_context.application.use_cases import GetPrincipalUseCase
from identity_access_management_context.domain.entities import ServiceAccount, User


@pytest.fixture
def use_case(principal_repository):
    return GetPrincipalUseCase(principal_repository)


def test_given_a_user_when_getting_it_then_it_is_named_as_a_user(use_case, user_repository):
    user = User(id=uuid4(), username="ada", email="ada@example.com", name="Ada Lovelace")
    user_repository.save(user)

    assert use_case.execute(GetPrincipalCommand(principal_id=user.id)) == GetPrincipalResponse(
        principal_id=user.id, kind="user", display_name="Ada Lovelace"
    )


def test_given_a_service_account_when_getting_it_then_it_is_named_as_a_service_account(
    use_case, service_account_repository
):
    account = ServiceAccount.create(group_id=uuid4(), name="nightly-deploy")
    service_account_repository.create([account])

    assert use_case.execute(GetPrincipalCommand(principal_id=account.id)) == GetPrincipalResponse(
        principal_id=account.id, kind="service_account", display_name="nightly-deploy"
    )


def test_given_no_such_principal_when_getting_it_then_nothing_is_returned(use_case):
    assert use_case.execute(GetPrincipalCommand(principal_id=uuid4())) is None
