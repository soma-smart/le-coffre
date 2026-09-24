from uuid import UUID

import pytest

from identity_access_management_context.application.commands import SearchUsersCommand
from identity_access_management_context.application.use_cases import SearchUsersUseCase
from identity_access_management_context.domain.entities import User

from ..fakes import FakeUserRepository


@pytest.fixture
def use_case(user_repository: FakeUserRepository):
    return SearchUsersUseCase(user_repository)


def _seed(user_repository: FakeUserRepository, **overrides) -> User:
    defaults = dict(
        id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        username="jdoe",
        email="jdoe@example.com",
        name="Jane Doe",
    )
    defaults.update(overrides)
    user = User(**defaults)
    user_repository.save(user)
    return user


def test_given_matching_name_when_searching_should_return_user(
    use_case: SearchUsersUseCase, user_repository: FakeUserRepository
):
    user = _seed(user_repository)

    result = use_case.execute(SearchUsersCommand(query="Jane"))

    assert result == [user]


def test_given_matching_username_when_searching_should_return_user(
    use_case: SearchUsersUseCase, user_repository: FakeUserRepository
):
    user = _seed(user_repository)

    result = use_case.execute(SearchUsersCommand(query="jdo"))

    assert result == [user]


def test_given_matching_id_substring_when_searching_should_return_user(
    use_case: SearchUsersUseCase, user_repository: FakeUserRepository
):
    user = _seed(user_repository)

    result = use_case.execute(SearchUsersCommand(query="123e4567"))

    assert result == [user]


def test_given_no_match_when_searching_should_return_empty_list(
    use_case: SearchUsersUseCase, user_repository: FakeUserRepository
):
    _seed(user_repository)

    result = use_case.execute(SearchUsersCommand(query="zzz"))

    assert result == []
