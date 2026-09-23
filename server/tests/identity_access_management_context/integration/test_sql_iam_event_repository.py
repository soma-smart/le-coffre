from datetime import datetime, timezone
from uuid import uuid4


def _append(repository, event_type: str, group_id):
    repository.append_event(
        event_id=uuid4(),
        event_type=event_type,
        occurred_on=datetime.now(timezone.utc),
        actor_user_id=uuid4(),
        event_data={"group_id": str(group_id), "user_id": str(uuid4())},
    )


def test_given_membership_events_when_listing_then_returns_all_known_event_types(
    sql_iam_event_repository,
):
    group_id = uuid4()

    for event_type in [
        "UserAddedToGroupEvent",
        "OwnerAddedToGroupEvent",
        "UserRemovedFromGroupEvent",
        "OwnerDemotedToMemberEvent",
    ]:
        _append(sql_iam_event_repository, event_type, group_id)

    events = sql_iam_event_repository.list_events(group_id)

    assert {event["event_type"] for event in events} == {
        "UserAddedToGroupEvent",
        "OwnerAddedToGroupEvent",
        "UserRemovedFromGroupEvent",
        "OwnerDemotedToMemberEvent",
    }


def test_given_unrelated_iam_event_when_listing_group_events_then_it_is_excluded(
    sql_iam_event_repository,
):
    group_id = uuid4()
    _append(sql_iam_event_repository, "OwnerDemotedToMemberEvent", group_id)
    # Not a group-membership event type — must never leak into group history.
    sql_iam_event_repository.append_event(
        event_id=uuid4(),
        event_type="UserCreatedEvent",
        occurred_on=datetime.now(timezone.utc),
        actor_user_id=uuid4(),
        event_data={"group_id": str(group_id)},
    )

    events = sql_iam_event_repository.list_events(group_id)

    assert [event["event_type"] for event in events] == ["OwnerDemotedToMemberEvent"]
