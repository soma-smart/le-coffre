from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from password_management_context.adapters.secondary.sql import SqlOneTimeLinkRepository
from password_management_context.domain.entities import OneTimeLink
from password_management_context.domain.value_objects import (
    OneTimeLinkLifetime,
    OneTimeLinkToken,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

PASSWORD_ID = uuid4()
CREATOR_ID = uuid4()


def _build_link(password_id=PASSWORD_ID, now=T0) -> OneTimeLink:
    return OneTimeLink.create(
        password_id=password_id,
        created_by_user_id=CREATOR_ID,
        token=OneTimeLinkToken.generate(),
        lifetime=OneTimeLinkLifetime.default(),
        now=now,
    )


def test_given_a_stored_link_when_fetching_by_token_hash_should_round_trip_it(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    link = _build_link()
    sql_one_time_link_repository.add(link)
    session.expunge_all()

    found = sql_one_time_link_repository.get_by_token_hash(link.token_hash)

    assert found is not None
    assert found.id == link.id
    assert found.password_id == PASSWORD_ID
    assert found.read_at is None
    assert found.revoked_at is None


def test_given_a_reloaded_link_when_checking_expiry_should_not_mix_naive_and_aware_datetimes(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """The column type is naive but the domain works in aware UTC. Without the
    mapper re-attaching UTC, is_expired raises TypeError for every link that is
    no longer in the session identity map, which is the normal case in
    production since each request gets a fresh session."""
    link = _build_link()
    sql_one_time_link_repository.add(link)
    session.expunge_all()

    reloaded = sql_one_time_link_repository.get_by_token_hash(link.token_hash)

    assert reloaded is not None
    assert reloaded.expires_at.tzinfo is not None
    assert reloaded.is_expired(T0 + timedelta(days=2)) is True
    assert reloaded.is_expired(T0) is False


def test_given_an_unknown_token_hash_when_fetching_should_return_none(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    assert sql_one_time_link_repository.get_by_token_hash("nope") is None


def test_given_a_link_when_consuming_twice_should_only_succeed_once(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    """The single-use guarantee lives in this conditional UPDATE. If it ever
    degrades into a read-then-write, two concurrent redemptions would both
    receive the secret and the feature would silently stop being one-time."""
    link = _build_link()
    sql_one_time_link_repository.add(link)

    assert sql_one_time_link_repository.consume(link.id, T0) is True
    assert sql_one_time_link_repository.consume(link.id, T0 + timedelta(seconds=1)) is False

    stored = sql_one_time_link_repository.get_by_id(link.id)
    assert stored is not None
    assert stored.read_at is not None


def test_given_a_revoked_link_when_consuming_should_fail(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    link = _build_link()
    sql_one_time_link_repository.add(link)
    sql_one_time_link_repository.revoke(link.id, T0)

    assert sql_one_time_link_repository.consume(link.id, T0) is False


def test_given_a_consumed_link_when_revoking_should_fail_and_preserve_the_read_timestamp(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    link = _build_link()
    sql_one_time_link_repository.add(link)
    sql_one_time_link_repository.consume(link.id, T0)

    assert sql_one_time_link_repository.revoke(link.id, T0 + timedelta(minutes=5)) is False

    stored = sql_one_time_link_repository.get_by_id(link.id)
    assert stored is not None
    assert stored.revoked_at is None
    assert stored.read_at is not None


def test_given_an_unknown_link_when_consuming_should_return_false(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    assert sql_one_time_link_repository.consume(uuid4(), T0) is False


def test_given_duplicate_token_hashes_when_storing_should_be_rejected_by_the_unique_index(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    link = _build_link()
    sql_one_time_link_repository.add(link)

    clash = _build_link()
    clash.token_hash = link.token_hash

    with pytest.raises(IntegrityError):
        sql_one_time_link_repository.add(clash)


def test_given_several_links_when_listing_should_return_most_recent_first_and_scope_by_password(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    older = _build_link(now=T0)
    newer = _build_link(now=T0 + timedelta(hours=1))
    other_password = _build_link(password_id=uuid4())
    for link in (older, newer, other_password):
        sql_one_time_link_repository.add(link)

    listed = sql_one_time_link_repository.list_for_password(PASSWORD_ID, limit=10)

    assert [link.id for link in listed] == [newer.id, older.id]


def test_given_links_when_deleting_for_a_password_should_only_drop_that_passwords_links(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    mine = _build_link()
    other = _build_link(password_id=uuid4())
    sql_one_time_link_repository.add(mine)
    sql_one_time_link_repository.add(other)

    sql_one_time_link_repository.delete_for_password(PASSWORD_ID)

    assert sql_one_time_link_repository.list_for_password(PASSWORD_ID, limit=10) == []
    assert sql_one_time_link_repository.get_by_id(other.id) is not None


def test_given_more_links_than_the_limit_when_listing_should_return_only_the_newest(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """The limit is applied in SQL, not after the fact: an unbounded query would
    still load every row for a password that has accumulated them for months."""
    for minute in range(25):
        sql_one_time_link_repository.add(_build_link(now=T0 + timedelta(minutes=minute)))
    session.expunge_all()

    listed = sql_one_time_link_repository.list_for_password(PASSWORD_ID, limit=10)

    assert len(listed) == 10
    assert listed[0].created_at == T0 + timedelta(minutes=24)
    assert listed[-1].created_at == T0 + timedelta(minutes=15)


def test_count_reports_every_link_regardless_of_the_listing_limit(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    for minute in range(25):
        sql_one_time_link_repository.add(_build_link(now=T0 + timedelta(minutes=minute)))
    sql_one_time_link_repository.add(_build_link(password_id=uuid4()))

    assert sql_one_time_link_repository.count_for_password(PASSWORD_ID) == 25


def test_active_count_excludes_read_revoked_and_expired_links(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """The creation cap is enforced from this count, so a link wrongly counted
    as active silently blocks the owner, and one wrongly counted as inactive
    silently lets the cap be exceeded."""
    fresh = _build_link()
    read = _build_link()
    revoked = _build_link()
    expired = OneTimeLink.create(
        password_id=PASSWORD_ID,
        created_by_user_id=CREATOR_ID,
        token=OneTimeLinkToken.generate(),
        lifetime=OneTimeLinkLifetime(seconds=600),
        now=T0,
    )
    for link in (fresh, read, revoked, expired):
        sql_one_time_link_repository.add(link)
    sql_one_time_link_repository.consume(read.id, T0)
    sql_one_time_link_repository.revoke(revoked.id, T0)
    session.expunge_all()

    # At T0 the short-lived link is still alive, so fresh + expired are active.
    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, T0) == 2
    # Once it has lapsed, only the fresh one remains.
    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, T0 + timedelta(hours=1)) == 1


def test_active_count_is_scoped_to_one_password(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    sql_one_time_link_repository.add(_build_link())
    sql_one_time_link_repository.add(_build_link(password_id=uuid4()))

    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, T0) == 1


def test_active_count_accepts_a_naive_instant_as_well_as_an_aware_one(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """The column is naive UTC while the domain clock is aware. A skew here
    would make the comparison silently wrong rather than fail loudly."""
    sql_one_time_link_repository.add(_build_link())
    session.expunge_all()

    aware = T0 + timedelta(hours=1)
    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, aware) == 1
    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, aware.replace(tzinfo=None)) == 1


def test_active_listing_returns_only_redeemable_links(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    alive = _build_link()
    read = _build_link()
    revoked = _build_link()
    for link in (alive, read, revoked):
        sql_one_time_link_repository.add(link)
    sql_one_time_link_repository.consume(read.id, T0)
    sql_one_time_link_repository.revoke(revoked.id, T0)
    session.expunge_all()

    listed = sql_one_time_link_repository.list_active_for_password(PASSWORD_ID, T0, limit=10)

    assert [link.id for link in listed] == [alive.id]


def test_active_listing_finds_a_link_buried_under_newer_spent_ones(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """Filtering has to happen in SQL. Fetching the newest N and filtering
    afterwards would lose this link entirely, leaving the owner unable to revoke
    a grant that is still live."""
    buried = _build_link(now=T0)
    sql_one_time_link_repository.add(buried)
    for minute in range(1, 21):
        spent = _build_link(now=T0 + timedelta(minutes=minute))
        sql_one_time_link_repository.add(spent)
        sql_one_time_link_repository.consume(spent.id, T0 + timedelta(minutes=minute))
    session.expunge_all()

    listed = sql_one_time_link_repository.list_active_for_password(PASSWORD_ID, T0 + timedelta(hours=1), limit=10)

    assert [link.id for link in listed] == [buried.id]


def test_active_listing_drops_expired_links(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    short_lived = OneTimeLink.create(
        password_id=PASSWORD_ID,
        created_by_user_id=CREATOR_ID,
        token=OneTimeLinkToken.generate(),
        lifetime=OneTimeLinkLifetime(seconds=600),
        now=T0,
    )
    sql_one_time_link_repository.add(short_lived)

    assert len(sql_one_time_link_repository.list_active_for_password(PASSWORD_ID, T0, limit=10)) == 1
    assert sql_one_time_link_repository.list_active_for_password(PASSWORD_ID, T0 + timedelta(hours=1), limit=10) == []


def test_writes_normalise_a_non_utc_instant_before_storing_it(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """The column is naive, so an aware value is stored by dropping its offset,
    not by converting it. Under a UTC+2 clock a 10-minute link would then be
    stamped two hours ahead and outlive its lifetime by that much, because
    expiry is compared against a correctly normalised `now`."""
    paris = timezone(timedelta(hours=2))
    created_at = datetime(2026, 1, 1, 14, 0, 0, tzinfo=paris)  # 12:00 UTC
    link = OneTimeLink.create(
        password_id=PASSWORD_ID,
        created_by_user_id=CREATOR_ID,
        token=OneTimeLinkToken.generate(),
        lifetime=OneTimeLinkLifetime(seconds=600),
        now=created_at,
    )
    sql_one_time_link_repository.add(link)
    session.expunge_all()

    stored = sql_one_time_link_repository.get_by_id(link.id)
    assert stored is not None
    assert stored.created_at == datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    # 30 minutes past a 10-minute lifetime: expired, whatever clock was used.
    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, created_at) == 1
    assert sql_one_time_link_repository.count_active_for_password(PASSWORD_ID, created_at + timedelta(minutes=30)) == 0


def test_consume_and_revoke_normalise_a_non_utc_instant(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    paris = timezone(timedelta(hours=2))
    stamped_at = datetime(2026, 1, 1, 14, 0, 0, tzinfo=paris)  # 12:00 UTC
    read = _build_link()
    revoked = _build_link()
    sql_one_time_link_repository.add(read)
    sql_one_time_link_repository.add(revoked)

    sql_one_time_link_repository.consume(read.id, stamped_at)
    sql_one_time_link_repository.revoke(revoked.id, stamped_at)
    session.expunge_all()

    expected = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert sql_one_time_link_repository.get_by_id(read.id).read_at == expected  # type: ignore[union-attr]
    assert sql_one_time_link_repository.get_by_id(revoked.id).revoked_at == expected  # type: ignore[union-attr]
