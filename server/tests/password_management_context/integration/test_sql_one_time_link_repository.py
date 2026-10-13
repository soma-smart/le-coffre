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


def _build_link(password_id=PASSWORD_ID, now=T0, **options) -> OneTimeLink:
    return OneTimeLink.create(
        password_id=password_id,
        created_by_user_id=CREATOR_ID,
        token=OneTimeLinkToken.generate(),
        lifetime=OneTimeLinkLifetime.default(),
        now=now,
        **options,
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


def test_vault_wide_listing_filters_in_the_query_not_after_truncation(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """An old live link can sit behind many newer spent ones. Fetching the newest
    N and filtering afterwards would drop it, leaving an admin unable to revoke a
    grant that is still open."""
    buried = _build_link(now=T0)
    sql_one_time_link_repository.add(buried)
    for minute in range(1, 21):
        spent = _build_link(password_id=uuid4(), now=T0 + timedelta(minutes=minute))
        sql_one_time_link_repository.add(spent)
        sql_one_time_link_repository.consume(spent.id, T0 + timedelta(minutes=minute))
    session.expunge_all()

    active = sql_one_time_link_repository.list_all(T0 + timedelta(hours=1), include_inactive=False, limit=10)

    assert [link.id for link in active] == [buried.id]
    assert sql_one_time_link_repository.count_all_matching(T0 + timedelta(hours=1), include_inactive=False) == 1
    assert sql_one_time_link_repository.count_all_matching(T0 + timedelta(hours=1), include_inactive=True) == 21


def test_listing_for_creator_is_scoped_to_that_user(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    other_creator = uuid4()
    mine = _build_link()
    theirs = _build_link()
    theirs.created_by_user_id = other_creator
    sql_one_time_link_repository.add(mine)
    sql_one_time_link_repository.add(theirs)

    listed = sql_one_time_link_repository.list_for_creator(CREATOR_ID, T0, include_inactive=False, limit=10)

    assert [link.id for link in listed] == [mine.id]
    assert sql_one_time_link_repository.count_for_creator(CREATOR_ID, T0, include_inactive=False) == 1


def test_bulk_revoke_spares_read_links_and_other_users(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    other_creator = uuid4()
    live = _build_link()
    read = _build_link()
    theirs = _build_link()
    theirs.created_by_user_id = other_creator
    for link in (live, read, theirs):
        sql_one_time_link_repository.add(link)
    sql_one_time_link_repository.consume(read.id, T0)
    session.expunge_all()

    revoked = sql_one_time_link_repository.revoke_all_for_creator(CREATOR_ID, T0 + timedelta(minutes=5))

    assert revoked == 1
    assert sql_one_time_link_repository.get_by_id(live.id).is_revoked()  # type: ignore[union-attr]
    # The read timestamp is the audit trail of a real disclosure: never overwritten.
    assert sql_one_time_link_repository.get_by_id(read.id).read_at is not None  # type: ignore[union-attr]
    assert not sql_one_time_link_repository.get_by_id(read.id).is_revoked()  # type: ignore[union-attr]
    assert not sql_one_time_link_repository.get_by_id(theirs.id).is_revoked()  # type: ignore[union-attr]


# ── Notification options and the expiry sweep ─────────────────────────


def test_given_a_link_without_options_when_reloading_should_have_both_flags_false(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    link = _build_link()
    sql_one_time_link_repository.add(link)
    session.expunge_all()

    found = sql_one_time_link_repository.get_by_id(link.id)

    assert found is not None
    assert (found.notify_on_read, found.notify_on_expiry, found.expiry_notified_at) == (False, False, None)


def test_given_notification_options_when_reloading_should_round_trip_them(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    link = _build_link(notify_on_read=True, notify_on_expiry=True)
    sql_one_time_link_repository.add(link)
    session.expunge_all()

    found = sql_one_time_link_repository.get_by_id(link.id)

    assert found is not None
    assert (found.notify_on_read, found.notify_on_expiry) == (True, True)


def _expired_at(link: OneTimeLink) -> datetime:
    return link.expires_at + timedelta(seconds=1)


def test_given_a_mix_of_links_when_listing_expired_pending_should_return_only_the_eligible_one(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    eligible = _build_link(notify_on_expiry=True)
    not_opted_in = _build_link()
    not_expired_yet = _build_link(now=T0 + timedelta(days=3), notify_on_expiry=True)
    already_read = _build_link(notify_on_expiry=True)
    revoked = _build_link(notify_on_expiry=True)
    already_claimed = _build_link(notify_on_expiry=True)
    for link in (eligible, not_opted_in, not_expired_yet, already_read, revoked, already_claimed):
        sql_one_time_link_repository.add(link)
    sql_one_time_link_repository.consume(already_read.id, T0)
    sql_one_time_link_repository.revoke(revoked.id, T0)
    sql_one_time_link_repository.claim_expiry_notification(already_claimed.id, T0)

    now = _expired_at(eligible)
    found = sql_one_time_link_repository.list_expired_pending_notification(now, limit=100)

    assert [link.id for link in found] == [eligible.id]


def test_given_a_link_at_its_exact_expiry_instant_when_listing_expired_pending_should_include_it(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    """Same boundary as OneTimeLink.is_expired: `now >= expires_at` is expired."""
    link = _build_link(notify_on_expiry=True)
    sql_one_time_link_repository.add(link)

    assert sql_one_time_link_repository.list_expired_pending_notification(link.expires_at, limit=10)
    assert not sql_one_time_link_repository.list_expired_pending_notification(
        link.expires_at - timedelta(microseconds=1), limit=10
    )


def test_given_many_expired_links_when_listing_expired_pending_should_honour_the_limit_oldest_first(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    links = [_build_link(now=T0 + timedelta(minutes=minute), notify_on_expiry=True) for minute in (5, 1, 3, 2, 4)]
    for link in links:
        sql_one_time_link_repository.add(link)

    found = sql_one_time_link_repository.list_expired_pending_notification(T0 + timedelta(days=30), limit=3)

    assert [link.created_at for link in found] == [T0 + timedelta(minutes=minute) for minute in (1, 2, 3)]


def test_given_a_link_when_claiming_its_expiry_twice_should_only_succeed_once(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """Same guard as consume(): the conditional UPDATE is what keeps two replicas
    from both publishing the expiry of the same link."""
    link = _build_link(notify_on_expiry=True)
    sql_one_time_link_repository.add(link)
    claimed_at = _expired_at(link)

    first = sql_one_time_link_repository.claim_expiry_notification(link.id, claimed_at)
    second = sql_one_time_link_repository.claim_expiry_notification(link.id, claimed_at)

    assert (first, second) == (True, False)
    session.expunge_all()
    stored = sql_one_time_link_repository.get_by_id(link.id)
    assert stored is not None
    assert stored.expiry_notified_at == claimed_at


def test_given_a_claimed_link_should_leave_the_expired_pending_listing(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
):
    link = _build_link(notify_on_expiry=True)
    sql_one_time_link_repository.add(link)
    now = _expired_at(link)
    sql_one_time_link_repository.claim_expiry_notification(link.id, now)

    assert sql_one_time_link_repository.list_expired_pending_notification(now, limit=10) == []


@pytest.mark.parametrize("spent_by", ["read", "revoked"])
def test_given_a_read_or_revoked_link_when_claiming_its_expiry_should_fail_and_leave_it_untouched(
    spent_by: str,
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    link = _build_link(notify_on_expiry=True)
    sql_one_time_link_repository.add(link)
    if spent_by == "read":
        sql_one_time_link_repository.consume(link.id, T0)
    else:
        sql_one_time_link_repository.revoke(link.id, T0)

    assert sql_one_time_link_repository.claim_expiry_notification(link.id, _expired_at(link)) is False

    session.expunge_all()
    stored = sql_one_time_link_repository.get_by_id(link.id)
    assert stored is not None
    assert stored.expiry_notified_at is None


def test_given_a_link_whose_expiry_was_claimed_when_consuming_should_fail_and_leave_it_unread(
    sql_one_time_link_repository: SqlOneTimeLinkRepository,
    session,
):
    """The other half of the read/expiry race: a read that checked the expiry just
    before the link ran out must not land once the sweep has claimed it, or the
    creator would get both the "opened" and the "expired" email."""
    link = _build_link(notify_on_expiry=True)
    sql_one_time_link_repository.add(link)
    assert sql_one_time_link_repository.claim_expiry_notification(link.id, _expired_at(link)) is True

    assert sql_one_time_link_repository.consume(link.id, link.expires_at - timedelta(seconds=1)) is False

    session.expunge_all()
    stored = sql_one_time_link_repository.get_by_id(link.id)
    assert stored is not None
    assert stored.read_at is None


def test_given_two_sessions_when_claiming_the_same_link_should_yield_a_single_winner(database_engine):
    """The real concurrency shape: two replicas, two sessions, one row."""
    from sqlmodel import Session

    link = _build_link(notify_on_expiry=True)
    with Session(database_engine) as setup_session:
        SqlOneTimeLinkRepository(setup_session).add(link)

    with Session(database_engine) as first, Session(database_engine) as second:
        results = [
            SqlOneTimeLinkRepository(first).claim_expiry_notification(link.id, _expired_at(link)),
            SqlOneTimeLinkRepository(second).claim_expiry_notification(link.id, _expired_at(link)),
        ]

    assert sorted(results) == [False, True]
