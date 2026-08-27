"""The pairing flow: register, approve or deny, exchange.

The security-critical assertions live here rather than against the value
objects directly, following the repository convention: these rules are all
reachable through a use case, so pinning them at the source would be
duplication.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import (
    ApproveExtensionPairingCommand,
    DenyExtensionPairingCommand,
    ExchangeExtensionPairingCommand,
    GetExtensionPairingCommand,
    StartExtensionPairingCommand,
)
from identity_access_management_context.application.responses import (
    ExchangedExtensionTokenResponse,
    PendingExtensionPairingResponse,
)
from identity_access_management_context.application.use_cases import (
    ApproveExtensionPairingUseCase,
    DenyExtensionPairingUseCase,
    ExchangeExtensionPairingUseCase,
    GetExtensionPairingUseCase,
    StartExtensionPairingUseCase,
)
from identity_access_management_context.domain.entities import UserPassword
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingAlreadyResolvedError,
    ExtensionPairingDeniedError,
    ExtensionPairingExpiredError,
    ExtensionPairingNotFoundError,
    InvalidPkceVerifierError,
    TooManyActiveExtensionTokensError,
    UnsupportedPkceMethodError,
)
from identity_access_management_context.domain.value_objects import PkceVerifier
from shared_kernel.domain.entities import ValidatedUser

NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
PAIRING_LIFETIME = 300
TOKEN_LIFETIME = 30 * 86400
POLL_INTERVAL = 5


@pytest.fixture
def user():
    return ValidatedUser(user_id=uuid4(), email="alice@example.com", display_name="Alice", roles=["user"])


@pytest.fixture
def registered_user(user, user_password_repository):
    user_password_repository.save(
        UserPassword(
            id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            password_hash=b"hashed",
        )
    )
    return user


@pytest.fixture
def start_use_case(extension_pairing_repository, time_provider):
    time_provider.set_current_time(NOW)
    return StartExtensionPairingUseCase(
        extension_pairing_repository=extension_pairing_repository,
        time_provider=time_provider,
        pairing_lifetime_seconds=PAIRING_LIFETIME,
        poll_interval_seconds=POLL_INTERVAL,
    )


@pytest.fixture
def get_use_case(extension_pairing_repository, time_provider):
    return GetExtensionPairingUseCase(
        extension_pairing_repository=extension_pairing_repository,
        time_provider=time_provider,
    )


@pytest.fixture
def approve_use_case(extension_pairing_repository, extension_token_repository, time_provider):
    return ApproveExtensionPairingUseCase(
        extension_pairing_repository=extension_pairing_repository,
        extension_token_repository=extension_token_repository,
        time_provider=time_provider,
    )


@pytest.fixture
def deny_use_case(extension_pairing_repository, time_provider):
    return DenyExtensionPairingUseCase(
        extension_pairing_repository=extension_pairing_repository,
        time_provider=time_provider,
    )


@pytest.fixture
def exchange_use_case(
    extension_pairing_repository,
    extension_token_repository,
    user_password_repository,
    sso_user_repository,
    event_publisher,
    admin_event_repository,
    time_provider,
):
    return ExchangeExtensionPairingUseCase(
        extension_pairing_repository=extension_pairing_repository,
        extension_token_repository=extension_token_repository,
        user_password_repository=user_password_repository,
        sso_user_repository=sso_user_repository,
        event_publisher=event_publisher,
        admin_event_repository=admin_event_repository,
        time_provider=time_provider,
        token_lifetime_seconds=TOKEN_LIFETIME,
        poll_interval_seconds=POLL_INTERVAL,
    )


def _start(start_use_case, verifier: PkceVerifier, device_name="Chrome on macOS"):
    return start_use_case.execute(
        StartExtensionPairingCommand(
            code_challenge=verifier.challenge().value,
            code_challenge_method="S256",
            device_name=device_name,
            created_from_ip="203.0.113.5",
        )
    )


class TestStart:
    def test_should_return_a_user_code_and_expiry_when_starting_a_pairing(self, start_use_case):
        started = _start(start_use_case, PkceVerifier.generate())

        assert started.user_code
        assert started.expires_at == NOW + timedelta(seconds=PAIRING_LIFETIME)
        assert started.poll_interval_seconds == POLL_INTERVAL

    def test_should_reject_when_the_challenge_method_is_not_s256(self, start_use_case):
        # `plain` would make the challenge equal to the verifier, so anyone who
        # saw the request could redeem the pairing. Refusing it explicitly
        # rather than defaulting means a client cannot negotiate it away.
        with pytest.raises(UnsupportedPkceMethodError):
            start_use_case.execute(
                StartExtensionPairingCommand(
                    code_challenge="whatever",
                    code_challenge_method="plain",
                    device_name="Chrome",
                )
            )

    def test_should_return_different_codes_when_starting_two_pairings(self, start_use_case):
        first = _start(start_use_case, PkceVerifier.generate())
        second = _start(start_use_case, PkceVerifier.generate())

        assert first.user_code != second.user_code

    def test_should_strip_and_truncate_when_the_device_name_is_hostile(
        self, start_use_case, extension_pairing_repository
    ):
        # Self-reported, and rendered on the approval page. Control characters
        # would let a caller forge line breaks there and in log lines.
        _start(start_use_case, PkceVerifier.generate(), device_name="Evil\nName\r\twith control chars" + "x" * 200)

        stored = next(iter(extension_pairing_repository.pairings.values()))
        assert "\n" not in stored.device_name
        assert "\r" not in stored.device_name
        assert len(stored.device_name) <= 60

    def test_should_use_a_placeholder_when_the_device_name_is_empty(self, start_use_case, extension_pairing_repository):
        _start(start_use_case, PkceVerifier.generate(), device_name="   ")

        stored = next(iter(extension_pairing_repository.pairings.values()))
        assert stored.device_name == "Unnamed device"


class TestApprovalPage:
    def test_should_return_the_server_vouched_facts_when_loading_the_approval_page(
        self, start_use_case, get_use_case, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())

        details = get_use_case.execute(GetExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

        assert details.user_code == started.user_code
        assert details.device_name == "Chrome on macOS"
        # The requesting IP is what gives away a remote attacker who started
        # the pairing, so the page needs it.
        assert details.created_from_ip == "203.0.113.5"
        assert details.is_resolved is False

    def test_should_report_missing_when_the_pairing_has_expired(
        self, start_use_case, get_use_case, time_provider, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())

        time_provider.set_current_time(NOW + timedelta(seconds=PAIRING_LIFETIME + 1))

        with pytest.raises(ExtensionPairingNotFoundError):
            get_use_case.execute(GetExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

    def test_should_report_missing_when_the_code_is_malformed(self, get_use_case, user):
        # Same outcome as a code that simply does not exist, so well-formedness
        # cannot be used as a probe.
        with pytest.raises(ExtensionPairingNotFoundError):
            get_use_case.execute(GetExtensionPairingCommand(user_code="not-a-code", requesting_user=user))

    def test_should_report_missing_when_the_code_is_unknown(self, get_use_case, user):
        with pytest.raises(ExtensionPairingNotFoundError):
            get_use_case.execute(GetExtensionPairingCommand(user_code="ABCD-EFGH", requesting_user=user))


class TestApprove:
    def test_should_bind_the_pairing_to_the_user_when_approving(
        self, start_use_case, approve_use_case, extension_pairing_repository, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())

        approve_use_case.execute(ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

        stored = next(iter(extension_pairing_repository.pairings.values()))
        assert stored.approved_by_user_id == user.user_id
        assert stored.approved_at == NOW

    def test_should_mint_no_credential_when_approving(
        self, start_use_case, approve_use_case, extension_token_repository, user
    ):
        # The token is created during the exchange, so its plaintext never has
        # to wait anywhere for the extension to collect it.
        started = _start(start_use_case, PkceVerifier.generate())

        approve_use_case.execute(ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

        assert extension_token_repository.tokens == {}

    def test_should_approve_when_the_code_is_lowercase(
        self, start_use_case, approve_use_case, extension_pairing_repository, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())

        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=f"  {started.user_code.lower()}  ", requesting_user=user)
        )

        stored = next(iter(extension_pairing_repository.pairings.values()))
        assert stored.approved_by_user_id == user.user_id

    def test_should_refuse_when_approving_twice(self, start_use_case, approve_use_case, user):
        started = _start(start_use_case, PkceVerifier.generate())
        command = ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=user)
        approve_use_case.execute(command)

        with pytest.raises(ExtensionPairingAlreadyResolvedError):
            approve_use_case.execute(command)

    def test_should_refuse_when_approving_an_expired_pairing(
        self, start_use_case, approve_use_case, time_provider, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())

        time_provider.set_current_time(NOW + timedelta(seconds=PAIRING_LIFETIME + 1))

        with pytest.raises(ExtensionPairingExpiredError):
            approve_use_case.execute(ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

    def test_should_refuse_when_the_user_is_at_the_device_cap(
        self, start_use_case, approve_use_case, extension_token_repository, user
    ):
        # Checked at approval, while the user is still looking at a screen that
        # can explain it, rather than letting the extension fail silently later.
        from identity_access_management_context.domain.entities import ExtensionToken
        from identity_access_management_context.domain.value_objects import ExtensionTokenSecret

        for _ in range(5):
            extension_token_repository.add(
                ExtensionToken.create(
                    user_id=user.user_id,
                    secret=ExtensionTokenSecret.generate(),
                    device_name="existing",
                    lifetime=timedelta(seconds=TOKEN_LIFETIME),
                    now=NOW,
                )
            )
        started = _start(start_use_case, PkceVerifier.generate())

        with pytest.raises(TooManyActiveExtensionTokensError):
            approve_use_case.execute(ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=user))


class TestDeny:
    def test_should_mark_the_pairing_denied_when_denying(
        self, start_use_case, deny_use_case, extension_pairing_repository, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())

        deny_use_case.execute(DenyExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

        stored = next(iter(extension_pairing_repository.pairings.values()))
        assert stored.denied_at == NOW
        assert stored.approved_at is None

    def test_should_refuse_when_denying_an_approved_pairing(
        self, start_use_case, approve_use_case, deny_use_case, user
    ):
        started = _start(start_use_case, PkceVerifier.generate())
        approve_use_case.execute(ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=user))

        with pytest.raises(ExtensionPairingAlreadyResolvedError):
            deny_use_case.execute(DenyExtensionPairingCommand(user_code=started.user_code, requesting_user=user))


class TestExchange:
    def test_should_mint_a_credential_for_the_approver_when_exchanging(
        self, start_use_case, approve_use_case, exchange_use_case, registered_user
    ):
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )

        result = exchange_use_case.execute(
            ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)
        )

        assert isinstance(result, ExchangedExtensionTokenResponse)
        assert result.user_id == registered_user.user_id
        assert result.email == registered_user.email
        assert result.expires_at == NOW + timedelta(seconds=TOKEN_LIFETIME)
        assert len(result.token) >= 43

    def test_should_store_only_the_hash_when_exchanging(
        self, start_use_case, approve_use_case, exchange_use_case, extension_token_repository, registered_user
    ):
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )

        result = exchange_use_case.execute(
            ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)
        )

        stored = extension_token_repository.tokens[result.token_id]
        # The plaintext exists in this response and in the extension's storage,
        # nowhere else.
        assert stored.token_hash != result.token
        assert result.token not in stored.token_hash

    def test_should_reject_when_the_verifier_is_wrong(
        self, start_use_case, approve_use_case, exchange_use_case, registered_user
    ):
        # The binding that stops someone who merely read the user_code off the
        # screen, or out of the URL fragment, from redeeming the pairing.
        started = _start(start_use_case, PkceVerifier.generate())
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )

        with pytest.raises(InvalidPkceVerifierError):
            exchange_use_case.execute(
                ExchangeExtensionPairingCommand(
                    user_code=started.user_code, code_verifier=PkceVerifier.generate().value
                )
            )

    def test_should_mint_nothing_when_the_verifier_is_wrong(
        self, start_use_case, approve_use_case, exchange_use_case, extension_token_repository, registered_user
    ):
        started = _start(start_use_case, PkceVerifier.generate())
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )

        with pytest.raises(InvalidPkceVerifierError):
            exchange_use_case.execute(
                ExchangeExtensionPairingCommand(
                    user_code=started.user_code, code_verifier=PkceVerifier.generate().value
                )
            )

        assert extension_token_repository.tokens == {}

    def test_should_report_pending_when_the_pairing_is_unapproved(
        self, start_use_case, exchange_use_case, registered_user
    ):
        # Only reachable with a matching verifier, so "pending" is never an
        # oracle for anyone who cannot already prove they own the pairing.
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)

        result = exchange_use_case.execute(
            ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)
        )

        assert isinstance(result, PendingExtensionPairingResponse)
        assert result.poll_interval_seconds == POLL_INTERVAL

    def test_should_refuse_when_exchanging_a_denied_pairing(
        self, start_use_case, deny_use_case, exchange_use_case, registered_user
    ):
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)
        deny_use_case.execute(DenyExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user))

        with pytest.raises(ExtensionPairingDeniedError):
            exchange_use_case.execute(
                ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)
            )

    def test_should_refuse_when_exchanging_an_expired_pairing(
        self, start_use_case, approve_use_case, exchange_use_case, time_provider, registered_user
    ):
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )

        time_provider.set_current_time(NOW + timedelta(seconds=PAIRING_LIFETIME + 1))

        with pytest.raises(ExtensionPairingExpiredError):
            exchange_use_case.execute(
                ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)
            )

    def test_should_yield_exactly_one_credential_when_exchanging_twice(
        self, start_use_case, approve_use_case, exchange_use_case, extension_token_repository, registered_user
    ):
        # The single-mint guarantee. A second exchange must not walk away with
        # another credential from the same approval.
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )
        command = ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)

        exchange_use_case.execute(command)

        with pytest.raises(ExtensionPairingAlreadyResolvedError):
            exchange_use_case.execute(command)
        assert len(extension_token_repository.tokens) == 1

    def test_should_record_an_audit_event_when_exchanging(
        self, start_use_case, approve_use_case, exchange_use_case, admin_event_repository, registered_user
    ):
        verifier = PkceVerifier.generate()
        started = _start(start_use_case, verifier)
        approve_use_case.execute(
            ApproveExtensionPairingCommand(user_code=started.user_code, requesting_user=registered_user)
        )

        exchange_use_case.execute(
            ExchangeExtensionPairingCommand(user_code=started.user_code, code_verifier=verifier.value)
        )

        assert any(event["event_type"] == "ExtensionPairedEvent" for event in admin_event_repository.events)
