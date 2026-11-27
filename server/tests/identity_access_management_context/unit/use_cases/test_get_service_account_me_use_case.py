from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import GetServiceAccountMeCommand
from identity_access_management_context.application.responses import GetServiceAccountMeResponse
from identity_access_management_context.application.use_cases import GetServiceAccountMeUseCase
from identity_access_management_context.domain.entities import Group, ServiceAccount
from identity_access_management_context.domain.exceptions import ServiceAccountNotFoundException


@pytest.fixture
def use_case(service_account_repository, group_repository):
    return GetServiceAccountMeUseCase(service_account_repository, group_repository)


def test_given_an_account_when_asking_who_it_is_then_its_group_is_named(
    use_case, service_account_repository, group_repository
):
    group = Group(id=uuid4(), name="Deployments", is_personal=False)
    group_repository.save_group(group)
    account = ServiceAccount.create(group_id=group.id, name="nightly-deploy")
    service_account_repository.create([account])

    response = use_case.execute(GetServiceAccountMeCommand(service_account_id=account.id))

    assert response == GetServiceAccountMeResponse(
        service_account_id=account.id, name="nightly-deploy", group_id=group.id, group_name="Deployments"
    )


def test_given_an_unknown_account_when_asking_who_it_is_then_it_is_refused(use_case):
    with pytest.raises(ServiceAccountNotFoundException):
        use_case.execute(GetServiceAccountMeCommand(service_account_id=uuid4()))
