from datetime import UTC, datetime, timedelta
from uuid import uuid4

from identity_access_management_context.domain.entities import MAX_ACTIVE_TOKENS_PER_USER, ExtensionToken
from identity_access_management_context.domain.value_objects import ExtensionTokenSecret

NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
THIRTY_DAYS = timedelta(days=30)


def _add(repository, token):
    """Seed one token, failing loudly if the device cap swallowed it."""
    stored = repository.add(token, MAX_ACTIVE_TOKENS_PER_USER, token.created_at)
    assert stored is not None
    return stored


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
    def test_should_store_only_the_hash_when_adding_a_token(self, sql_extension_token_repository):
        secret = ExtensionTokenSecret.generate()
        stored = _add(sql_extension_token_repository, _token(secret=secret))

        found = sql_extension_token_repository.get_by_token_hash(secret.hashed())

        assert found is not None
        assert found.id == stored.id
        # The plaintext must never be recoverable from storage.
        assert secret.value not in found.token_hash

    def test_should_find_nothing_when_the_hash_is_unknown(self, sql_extension_token_repository):
        _add(sql_extension_token_repository, _token())

        assert sql_extension_token_repository.get_by_token_hash("deadbeef") is None

    def test_should_return_aware_utc_when_reading_timestamps_back(self, sql_extension_token_repository):
        stored = _add(sql_extension_token_repository, _token())

        found = sql_extension_token_repository.get_by_id(stored.id)

        # SQLite hands back naive datetimes; expiry is compared against an aware
        # `now`, so a repository that forgets to re-attach UTC would make every
        # token look valid (or expired) by the size of the local offset.
        assert found.created_at.tzinfo is not None
        assert found.created_at == NOW
        assert found.expires_at == NOW + THIRTY_DAYS

    def test_should_list_newest_first_including_dead_ones_when_listing_for_a_user(self, sql_extension_token_repository):
        user_id = uuid4()
        older = _add(sql_extension_token_repository, _token(user_id=user_id, now=NOW - timedelta(days=2)))
        newer = _add(sql_extension_token_repository, _token(user_id=user_id, now=NOW))
        sql_extension_token_repository.revoke(older.id, NOW)
        _add(sql_extension_token_repository, _token(user_id=uuid4()))

        listed = sql_extension_token_repository.list_for_user(user_id)

        # Revoked rows stay listed: the connected-devices screen shows history,
        # and the row is retained for audit rather than deleted.
        assert [t.id for t in listed] == [newer.id, older.id]


class TestDeviceCap:
    """The cap has to be part of the insert, not a question asked before it.

    ApproveExtensionPairingUseCase checks it minutes earlier and against a
    different pairing, so on its own it bounds nothing.
    """

    def test_should_refuse_the_insert_when_the_user_is_at_the_cap(self, sql_extension_token_repository):
        user_id = uuid4()
        for _ in range(2):
            sql_extension_token_repository.add(_token(user_id=user_id), 2, NOW)

        refused = sql_extension_token_repository.add(_token(user_id=user_id), 2, NOW)

        assert refused is None
        assert sql_extension_token_repository.count_active_for_user(user_id, NOW) == 2

    def test_should_write_no_row_when_the_cap_refuses(self, sql_extension_token_repository):
        # A refusal that still wrote the row would hand out a working
        # credential while reporting failure.
        user_id = uuid4()
        sql_extension_token_repository.add(_token(user_id=user_id), 1, NOW)
        rejected = _token(user_id=user_id)

        sql_extension_token_repository.add(rejected, 1, NOW)

        assert sql_extension_token_repository.get_by_id(rejected.id) is None

    def test_should_free_a_slot_when_a_token_is_revoked(self, sql_extension_token_repository):
        user_id = uuid4()
        first = sql_extension_token_repository.add(_token(user_id=user_id), 1, NOW)
        sql_extension_token_repository.revoke(first.id, NOW)

        stored = sql_extension_token_repository.add(_token(user_id=user_id), 1, NOW)

        assert stored is not None

    def test_should_ignore_other_users_when_applying_the_cap(self, sql_extension_token_repository):
        user_id = uuid4()
        for _ in range(3):
            sql_extension_token_repository.add(_token(user_id=uuid4()), 1, NOW)

        stored = sql_extension_token_repository.add(_token(user_id=user_id), 1, NOW)

        assert stored is not None


class TestActiveCount:
    def test_should_count_only_live_tokens_when_counting_active(self, sql_extension_token_repository):
        user_id = uuid4()
        _add(sql_extension_token_repository, _token(user_id=user_id))
        revoked = _add(sql_extension_token_repository, _token(user_id=user_id))
        _add(sql_extension_token_repository, _token(user_id=user_id, lifetime=timedelta(seconds=1)))
        sql_extension_token_repository.revoke(revoked.id, NOW)

        # One live, one revoked, one expired by the time we look.
        assert sql_extension_token_repository.count_active_for_user(user_id, NOW + timedelta(minutes=1)) == 1

    def test_should_not_count_when_tokens_belong_to_another_user(self, sql_extension_token_repository):
        user_id = uuid4()
        _add(sql_extension_token_repository, _token(user_id=uuid4()))

        assert sql_extension_token_repository.count_active_for_user(user_id, NOW) == 0


class TestRevocation:
    def test_should_keep_the_first_timestamp_when_revoking_twice(self, sql_extension_token_repository):
        stored = _add(sql_extension_token_repository, _token())

        assert sql_extension_token_repository.revoke(stored.id, NOW) is True
        # The second call must report that it changed nothing, and must not move
        # the timestamp: the audit trail records when access actually stopped.
        assert sql_extension_token_repository.revoke(stored.id, NOW + timedelta(hours=1)) is False
        assert sql_extension_token_repository.get_by_id(stored.id).revoked_at == NOW

    def test_should_report_no_change_when_revoking_an_unknown_token(self, sql_extension_token_repository):
        assert sql_extension_token_repository.revoke(uuid4(), NOW) is False

    def test_should_touch_only_the_users_live_tokens_when_revoking_all(self, sql_extension_token_repository):
        user_id = uuid4()
        first = _add(sql_extension_token_repository, _token(user_id=user_id))
        second = _add(sql_extension_token_repository, _token(user_id=user_id))
        already_revoked = _add(sql_extension_token_repository, _token(user_id=user_id))
        other_user_token = _add(sql_extension_token_repository, _token(user_id=uuid4()))
        sql_extension_token_repository.revoke(already_revoked.id, NOW - timedelta(days=1))

        revoked_count = sql_extension_token_repository.revoke_all_for_user(user_id, NOW)

        assert revoked_count == 2
        assert sql_extension_token_repository.get_by_id(first.id).revoked_at == NOW
        assert sql_extension_token_repository.get_by_id(second.id).revoked_at == NOW
        # Untouched: already dead, and belonging to someone else.
        assert sql_extension_token_repository.get_by_id(already_revoked.id).revoked_at == NOW - timedelta(days=1)
        assert sql_extension_token_repository.get_by_id(other_user_token.id).revoked_at is None

    def test_should_report_zero_when_nothing_is_live(self, sql_extension_token_repository):
        assert sql_extension_token_repository.revoke_all_for_user(uuid4(), NOW) == 0


class TestLastUsed:
    def test_should_record_when_the_credential_is_used_for_the_first_time(self, sql_extension_token_repository):
        stored = _add(sql_extension_token_repository, _token())

        sql_extension_token_repository.touch_last_used(stored.id, NOW, coarsen_to_seconds=300)

        assert sql_extension_token_repository.get_by_id(stored.id).last_used_at == NOW

    def test_should_not_write_when_a_second_use_falls_inside_the_coarsening_window(
        self, sql_extension_token_repository
    ):
        stored = _add(sql_extension_token_repository, _token())
        sql_extension_token_repository.touch_last_used(stored.id, NOW, coarsen_to_seconds=300)

        sql_extension_token_repository.touch_last_used(stored.id, NOW + timedelta(seconds=60), coarsen_to_seconds=300)

        # A busy extension must not write a row on every request; the column
        # only feeds a "last used" label where minutes of precision are ample.
        assert sql_extension_token_repository.get_by_id(stored.id).last_used_at == NOW

    def test_should_write_again_when_a_use_falls_past_the_coarsening_window(self, sql_extension_token_repository):
        stored = _add(sql_extension_token_repository, _token())
        sql_extension_token_repository.touch_last_used(stored.id, NOW, coarsen_to_seconds=300)

        later = NOW + timedelta(seconds=301)
        sql_extension_token_repository.touch_last_used(stored.id, later, coarsen_to_seconds=300)

        assert sql_extension_token_repository.get_by_id(stored.id).last_used_at == later

    def test_should_do_nothing_when_touching_an_unknown_token(self, sql_extension_token_repository):
        # Telemetry must never fail the caller: this is not part of authentication.
        sql_extension_token_repository.touch_last_used(uuid4(), NOW, coarsen_to_seconds=300)
