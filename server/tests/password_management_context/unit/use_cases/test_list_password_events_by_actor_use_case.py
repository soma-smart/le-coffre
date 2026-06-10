from datetime import datetime
from uuid import UUID

import pytest

from password_management_context.application.commands import (
    ListPasswordEventsByActorCommand,
)
from password_management_context.application.use_cases import (
    ListPasswordEventsByActorUseCase,
)
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser

from ..fakes import FakePasswordEventRepository

ADMIN_USER = AuthenticatedUser(user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"])
REGULAR_USER = AuthenticatedUser(user_id=UUID("9a742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=[])
TARGET_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
PASSWORD_ID_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PASSWORD_ID_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def use_case(password_event_repository: FakePasswordEventRepository):
    return ListPasswordEventsByActorUseCase(password_event_repository)


def _seed_events(repo: FakePasswordEventRepository):
    repo.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        password_id=PASSWORD_ID_A,
        actor_user_id=TARGET_USER_ID,
        event_data={"title": "Gmail"},
    )
    repo.append_event(
        event_id=UUID("a2222222-2222-2222-2222-222222222222"),
        event_type="PasswordAccessedEvent",
        occurred_on=datetime(2026, 2, 6, 12, 0, 0),
        password_id=PASSWORD_ID_B,
        actor_user_id=TARGET_USER_ID,
        event_data={},
    )
    # Action by another user — must not be returned
    repo.append_event(
        event_id=UUID("a3333333-3333-3333-3333-333333333333"),
        event_type="PasswordCreatedEvent",
        occurred_on=datetime(2026, 2, 6, 11, 0, 0),
        password_id=PASSWORD_ID_A,
        actor_user_id=OTHER_USER_ID,
        event_data={},
    )


def test_admin_lists_all_actions_of_a_given_user(
    use_case: ListPasswordEventsByActorUseCase,
    password_event_repository: FakePasswordEventRepository,
):
    _seed_events(password_event_repository)

    response = use_case.execute(
        ListPasswordEventsByActorCommand(
            actor_user_id=TARGET_USER_ID,
            requesting_user=ADMIN_USER,
        )
    )

    assert len(response.events) == 2
    # Sorted by occurred_on desc
    assert response.events[0].event_type == "PasswordAccessedEvent"
    assert response.events[0].password_id == str(PASSWORD_ID_B)
    assert response.events[1].event_type == "PasswordCreatedEvent"
    assert response.events[1].password_id == str(PASSWORD_ID_A)
    assert all(e.actor_user_id == str(TARGET_USER_ID) for e in response.events)


def test_non_admin_is_rejected(
    use_case: ListPasswordEventsByActorUseCase,
    password_event_repository: FakePasswordEventRepository,
):
    _seed_events(password_event_repository)

    with pytest.raises(NotAdminError):
        use_case.execute(
            ListPasswordEventsByActorCommand(
                actor_user_id=TARGET_USER_ID,
                requesting_user=REGULAR_USER,
            )
        )


def test_filter_by_event_type_and_date_range(
    use_case: ListPasswordEventsByActorUseCase,
    password_event_repository: FakePasswordEventRepository,
):
    _seed_events(password_event_repository)

    response = use_case.execute(
        ListPasswordEventsByActorCommand(
            actor_user_id=TARGET_USER_ID,
            requesting_user=ADMIN_USER,
            event_types=["PasswordCreatedEvent"],
            start_date=datetime(2026, 2, 6, 0, 0, 0),
            end_date=datetime(2026, 2, 6, 23, 59, 59),
        )
    )

    assert len(response.events) == 1
    assert response.events[0].event_type == "PasswordCreatedEvent"
    assert response.events[0].password_id == str(PASSWORD_ID_A)


def test_returns_empty_when_actor_has_no_events(
    use_case: ListPasswordEventsByActorUseCase,
):
    response = use_case.execute(
        ListPasswordEventsByActorCommand(
            actor_user_id=TARGET_USER_ID,
            requesting_user=ADMIN_USER,
        )
    )

    assert response.events == []
