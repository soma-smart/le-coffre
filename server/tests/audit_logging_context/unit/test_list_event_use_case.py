import pytest
from uuid import uuid4
from datetime import datetime

from audit_logging_context.application.use_cases.list_event_use_case import (
    ListEventUseCase,
)
from audit_logging_context.application.commands import ListEventCommand
from shared_kernel.domain.entities import DomainEvent, AuthenticatedUser
from shared_kernel.adapters.primary.exceptions import NotAdminError


@pytest.fixture
def use_case(event_repository):
    return ListEventUseCase(event_repository)


@pytest.fixture
def admin_user():
    return AuthenticatedUser(user_id=uuid4(), roles=["admin"])


@pytest.fixture
def regular_user():
    return AuthenticatedUser(user_id=uuid4(), roles=["user"])


def test_given_empty_event_list_when_admin_lists_events_then_return_empty_list(
    use_case, admin_user
):
    command = ListEventCommand(requesting_user=admin_user)
    response = use_case.execute(command)

    assert response.events == []


def test_given_non_empty_event_list_when_admin_lists_events_then_return_event_list(
    use_case,
    event_repository,
    admin_user,
):
    event1 = DomainEvent(uuid4(), datetime.now())
    event_repository.append_event(event1)
    command = ListEventCommand(requesting_user=admin_user)

    response = use_case.execute(command)

    assert response.events == [event1]


def test_given_non_admin_user_when_listing_events_then_raise_not_admin_error(
    use_case, regular_user
):
    command = ListEventCommand(requesting_user=regular_user)

    with pytest.raises(NotAdminError) as exc_info:
        use_case.execute(command)

    assert "administrators" in str(exc_info.value).lower()
