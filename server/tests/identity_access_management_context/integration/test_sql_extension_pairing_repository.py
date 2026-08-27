from datetime import UTC, datetime, timedelta
from uuid import uuid4

from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.value_objects import PairingUserCode, PkceVerifier

NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
FIVE_MINUTES = timedelta(minutes=5)


def _pairing(verifier=None, lifetime=FIVE_MINUTES, now=NOW, device_name="Chrome on macOS"):
    verifier = verifier or PkceVerifier.generate()
    return ExtensionPairing.create(
        user_code=PairingUserCode.generate(),
        code_challenge=verifier.challenge(),
        device_name=device_name,
        lifetime=lifetime,
        now=now,
        created_from_ip="203.0.113.5",
    )


class TestPersistence:
    def test_finds_a_pairing_by_its_user_code(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())

        found = sql_extension_pairing_repository.get_by_user_code(stored.user_code)

        assert found is not None
        assert found.id == stored.id
        assert found.device_name == "Chrome on macOS"
        assert found.created_from_ip == "203.0.113.5"

    def test_an_unknown_user_code_finds_nothing(self, sql_extension_pairing_repository):
        sql_extension_pairing_repository.add(_pairing())

        assert sql_extension_pairing_repository.get_by_user_code(PairingUserCode.generate()) is None

    def test_the_challenge_survives_the_round_trip_and_still_matches(self, sql_extension_pairing_repository):
        verifier = PkceVerifier.generate()
        stored = sql_extension_pairing_repository.add(_pairing(verifier=verifier))

        found = sql_extension_pairing_repository.get_by_user_code(stored.user_code)

        # The whole exchange hinges on this comparison working after a DB
        # round-trip, so pin it here rather than only against an in-memory VO.
        assert found.code_challenge.matches(verifier)
        assert not found.code_challenge.matches(PkceVerifier.generate())

    def test_round_trips_timestamps_as_aware_utc(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())

        found = sql_extension_pairing_repository.get_by_user_code(stored.user_code)

        assert found.created_at.tzinfo is not None
        assert found.created_at == NOW
        assert found.expires_at == NOW + FIVE_MINUTES


class TestResolution:
    def test_saves_an_approval(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())
        approver = uuid4()

        stored.approve(approver, NOW)
        sql_extension_pairing_repository.save(stored)

        found = sql_extension_pairing_repository.get_by_user_code(stored.user_code)
        assert found.approved_at == NOW
        assert found.approved_by_user_id == approver
        assert found.denied_at is None

    def test_saves_a_denial(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())

        stored.deny(NOW)
        sql_extension_pairing_repository.save(stored)

        found = sql_extension_pairing_repository.get_by_user_code(stored.user_code)
        assert found.denied_at == NOW
        assert found.approved_at is None

    def test_saving_an_unknown_pairing_is_harmless(self, sql_extension_pairing_repository):
        orphan = _pairing()
        orphan.approve(uuid4(), NOW)

        sql_extension_pairing_repository.save(orphan)

        assert sql_extension_pairing_repository.get_by_user_code(orphan.user_code) is None


class TestConsume:
    """The single-mint guarantee.

    `consume` is one conditional UPDATE rather than a read-then-write, so two
    simultaneous exchanges cannot both walk away with a credential. These are
    the tests that pin that guard.
    """

    def test_an_approved_pairing_can_be_consumed_once(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())
        stored.approve(uuid4(), NOW)
        sql_extension_pairing_repository.save(stored)

        assert sql_extension_pairing_repository.consume(stored.id, NOW) is True
        # The second caller loses the race and must be told so, or it would mint
        # a second credential from one approval.
        assert sql_extension_pairing_repository.consume(stored.id, NOW) is False

    def test_consuming_records_when_it_happened(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())
        stored.approve(uuid4(), NOW)
        sql_extension_pairing_repository.save(stored)

        sql_extension_pairing_repository.consume(stored.id, NOW)

        assert sql_extension_pairing_repository.get_by_user_code(stored.user_code).consumed_at == NOW

    def test_an_unapproved_pairing_cannot_be_consumed(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())

        # Belt to the use case's braces: even if a caller reached consume()
        # without checking approval, no credential comes out of it.
        assert sql_extension_pairing_repository.consume(stored.id, NOW) is False

    def test_a_denied_pairing_cannot_be_consumed(self, sql_extension_pairing_repository):
        stored = sql_extension_pairing_repository.add(_pairing())
        stored.deny(NOW)
        sql_extension_pairing_repository.save(stored)

        assert sql_extension_pairing_repository.consume(stored.id, NOW) is False

    def test_an_unknown_pairing_cannot_be_consumed(self, sql_extension_pairing_repository):
        assert sql_extension_pairing_repository.consume(uuid4(), NOW) is False


class TestPurge:
    def test_purges_only_pairings_past_the_cutoff(self, sql_extension_pairing_repository):
        expired = sql_extension_pairing_repository.add(_pairing(now=NOW - timedelta(hours=1)))
        live = sql_extension_pairing_repository.add(_pairing(now=NOW))

        sql_extension_pairing_repository.purge_expired(NOW)

        assert sql_extension_pairing_repository.get_by_user_code(expired.user_code) is None
        assert sql_extension_pairing_repository.get_by_user_code(live.user_code) is not None
