from uuid import uuid4

from identity_access_management_context.domain.entities import ServiceAccount, User


def test_given_a_user_when_getting_its_principal_then_the_user_is_returned(
    sql_principal_repository, sql_user_repository
):
    user = User(id=uuid4(), username="john", email="john@example.com", name="John Doe")
    sql_user_repository.save(user)

    assert sql_principal_repository.get_by_id(user.id) == user


def test_given_a_service_account_when_getting_its_principal_then_the_account_is_returned(
    sql_principal_repository, sql_service_account_repository
):
    account = ServiceAccount.create(group_id=uuid4(), name="nightly-backup")
    sql_service_account_repository.create([account])

    assert sql_principal_repository.get_by_id(account.id) == account


def test_given_no_such_principal_when_getting_it_then_nothing_is_returned(sql_principal_repository):
    assert sql_principal_repository.get_by_id(uuid4()) is None
