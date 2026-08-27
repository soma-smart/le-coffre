from datetime import UTC, datetime, timedelta
from uuid import uuid4

from identity_access_management_context.domain.entities import ExtensionToken
from identity_access_management_context.domain.value_objects import ExtensionTokenSecret

NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
THIRTY_DAYS = timedelta(days=30)


def _token(user_id=None, secret=None, lifetime=THIRTY_DAYS, now=NOW, device_name="Chrome on macOS"):
    return ExtensionToken.create(
        user_id=user_id or uuid4(),
        secret=secret or ExtensionTokenSecret.generate(),
        device_name=device_name,
        lifetime=lifetime,
        now=now,
        created_from_ip="203.0.113.5",
    )


class TestPersistence:
    def test_stores_only_the_hash_and_finds_the_token_by_it(self, sql_extension_token_repository):
        secret = ExtensionTokenSecret.generate()
        stored = sql_extension_token_repository.add(_token(secret=secret))

        found = sql_extension_token_repository.get_by_token_hash(secret.hashed())

        assert found is not None
        assert found.id == stored.id
        # The plaintext must never be recoverable from storage.
        assert secret.value not in found.token_hash

    def test_an_unknown_hash_finds_nothing(self, sql_extension_token_repository):
        sql_extension_token_repository.add(_token())

        assert sql_extension_token_repository.get_by_token_hash("deadbeef") is None

    def test_round_trips_timestamps_as_aware_utc(self, sql_extension_token_repository):
        stored = sql_extension_token_repository.add(_token())

        found = sql_extension_token_repository.get_by_id(stored.id)

        # SQLite hands back naive datetimes; expiry is compared against an aware
        # `now`, so a repository that forgets to re-attach UTC would make every
        # token look valid (or expired) by the size of the local offset.
        assert found.created_at.tzinfo is not None
        assert found.created_at == NOW
        assert found.expires_at == NOW + THIRTY_DAYS

    def test_lists_a_users_tokens_newest_first_including_dead_ones(self, sql_extension_token_repository):
        user_id = uuid4()
        older = sql_extension_token_repository.add(_token(user_id=user_id, now=NOW - timedelta(days=2)))
        newer = sql_extension_token_repository.add(_token(user_id=user_id, now=NOW))
        sql_extension_token_repository.revoke(older.id, NOW)
        sql_extension_token_repository.add(_token(user_id=uuid4()))

        listed = sql_extension_token_repository.list_for_user(user_id)

        # Revoked rows stay listed: the connected-devices screen shows history,
        # and the row is retained for audit rather than deleted.
        assert [t.id for t in listed] == [newer.id, older.id]


class TestActiveCount:
    def test_counts_only_tokens_that_are_neither_revoked_nor_expired(self, sql_extension_token_repository):
        user_id = uuid4()
        sql_extension_token_repository.add(_token(user_id=user_id))
        revoked = sql_extension_token_repository.add(_token(user_id=user_id))
        sql_extension_token_repository.add(_token(user_id=user_id, lifetime=timedelta(seconds=1)))
        sql_extension_token_repository.revoke(revoked.id, NOW)

        # One live, one revoked, one expired by the time we look.
        assert sql_extension_token_repository.count_active_for_user(user_id, NOW + timedelta(minutes=1)) == 1

    def test_does_not_count_another_users_tokens(self, sql_extension_token_repository):
        user_id = uuid4()
        sql_extension_token_repository.add(_token(user_id=uuid4()))

        assert sql_extension_token_repository.count_active_for_user(user_id, NOW) == 0


class TestRevocation:
    def test_revoking_twice_keeps_the_first_timestamp(self, sql_extension_token_repository):
        stored = sql_extension_token_repository.add(_token())

        assert sql_extension_token_repository.revoke(stored.id, NOW) is True
        # The second call must report that it changed nothing, and must not move
        # the timestamp: the audit trail records when access actually stopped.
        assert sql_extension_token_repository.revoke(stored.id, NOW + timedelta(hours=1)) is False
        assert sql_extension_token_repository.get_by_id(stored.id).revoked_at == NOW

    def test_revoking_an_unknown_token_reports_no_change(self, sql_extension_token_repository):
        assert sql_extension_token_repository.revoke(uuid4(), NOW) is False

    def test_revoke_all_touches_only_the_users_live_tokens(self, sql_extension_token_repository):
        user_id = uuid4()
        first = sql_extension_token_repository.add(_token(user_id=user_id))
        second = sql_extension_token_repository.add(_token(user_id=user_id))
        already_revoked = sql_extension_token_repository.add(_token(user_id=user_id))
        other_user_token = sql_extension_token_repository.add(_token(user_id=uuid4()))
        sql_extension_token_repository.revoke(already_revoked.id, NOW - timedelta(days=1))

        revoked_count = sql_extension_token_repository.revoke_all_for_user(user_id, NOW)

        assert revoked_count == 2
        assert sql_extension_token_repository.get_by_id(first.id).revoked_at == NOW
        assert sql_extension_token_repository.get_by_id(second.id).revoked_at == NOW
        # Untouched: already dead, and belonging to someone else.
        assert sql_extension_token_repository.get_by_id(already_revoked.id).revoked_at == NOW - timedelta(days=1)
        assert sql_extension_token_repository.get_by_id(other_user_token.id).revoked_at is None

    def test_revoke_all_reports_zero_when_nothing_is_live(self, sql_extension_token_repository):
        assert sql_extension_token_repository.revoke_all_for_user(uuid4(), NOW) == 0


class TestLastUsed:
    def test_first_use_is_always_recorded(self, sql_extension_token_repository):
        stored = sql_extension_token_repository.add(_token())

        sql_extension_token_repository.touch_last_used(stored.id, NOW, coarsen_to_seconds=300)

        assert sql_extension_token_repository.get_by_id(stored.id).last_used_at == NOW

    def test_a_second_use_inside_the_coarsening_window_does_not_write(self, sql_extension_token_repository):
        stored = sql_extension_token_repository.add(_token())
        sql_extension_token_repository.touch_last_used(stored.id, NOW, coarsen_to_seconds=300)

        sql_extension_token_repository.touch_last_used(stored.id, NOW + timedelta(seconds=60), coarsen_to_seconds=300)

        # A busy extension must not write a row on every request; the column
        # only feeds a "last used" label where minutes of precision are ample.
        assert sql_extension_token_repository.get_by_id(stored.id).last_used_at == NOW

    def test_a_use_past_the_window_writes_again(self, sql_extension_token_repository):
        stored = sql_extension_token_repository.add(_token())
        sql_extension_token_repository.touch_last_used(stored.id, NOW, coarsen_to_seconds=300)

        later = NOW + timedelta(seconds=301)
        sql_extension_token_repository.touch_last_used(stored.id, later, coarsen_to_seconds=300)

        assert sql_extension_token_repository.get_by_id(stored.id).last_used_at == later

    def test_touching_an_unknown_token_is_harmless(self, sql_extension_token_repository):
        # Telemetry must never fail the caller: this is not part of authentication.
        sql_extension_token_repository.touch_last_used(uuid4(), NOW, coarsen_to_seconds=300)
