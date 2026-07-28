from uuid import UUID

import pytest

from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.use_cases import (
    PasswordLoginUseCase,
)
from identity_access_management_context.domain.constants import ADMIN_ROLE
from identity_access_management_context.domain.entities import (
    User,
    UserPassword,
)
from identity_access_management_context.domain.events import (
    AdminLoginEvent,
    AdminLoginFailedEvent,
)
from identity_access_management_context.domain.exceptions import (
    AccountLockedException,
    AdminNotFoundException,
    InvalidCredentialsException,
)
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import (
    FakeLoginLockoutGateway,
    FakePasswordHashingGateway,
    FakeTokenGateway,
    FakeUserPasswordRepository,
    FakeUserRepository,
)


@pytest.fixture
def use_case(
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    auth_session_repository,
    password_hashing_gateway: FakePasswordHashingGateway,
    token_gateway: FakeTokenGateway,
    time_provider: FakeTimeGateway,
    event_publisher,
    admin_event_repository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    return PasswordLoginUseCase(
        user_password_repository,
        user_repository,
        auth_session_repository,
        password_hashing_gateway,
        token_gateway,
        time_provider,
        event_publisher,
        admin_event_repository,
        login_lockout_gateway,
    )


def test_should_authenticate_admin_and_return_jwt_token(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = use_case.execute(command)

    assert response.jwt_token == f"jwt_token_for_{user_id}_uniqueness"
    assert response.admin_id == user_id
    assert response.email == email
    # A successful login clears any failure state the lockout gateway was tracking.
    assert login_lockout_gateway.successful_login_calls == [email]
    assert login_lockout_gateway.failed_login_calls == []


def test_should_raise_exception_for_wrong_password(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")

    with pytest.raises(InvalidCredentialsException):
        use_case.execute(command)

    assert login_lockout_gateway.failed_login_calls == [email]


def test_should_raise_exception_for_non_existent_admin(
    use_case: PasswordLoginUseCase,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")

    with pytest.raises(AdminNotFoundException):
        use_case.execute(command)

    assert login_lockout_gateway.failed_login_calls == ["nonexistent@lecoffre.com"]


def test_should_return_refresh_token_on_successful_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")

    response = use_case.execute(command)

    assert response.refresh_token == f"refresh_token_for_{user_id}_uniqueness"
    assert response.refresh_token != response.jwt_token


def test_should_publish_admin_login_event_on_successful_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)
    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginEvent)
    assert len(events) == 1
    assert events[0].admin_id == user_id
    assert events[0].email == email


def test_should_publish_admin_login_failed_event_on_wrong_password(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    event_publisher: FakeDomainEventPublisher,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")
    with pytest.raises(InvalidCredentialsException):
        use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginFailedEvent)
    assert len(events) == 1
    assert events[0].email == email
    assert events[0].reason == "Invalid credentials"


def test_should_publish_admin_login_failed_event_on_non_existent_admin(
    use_case: PasswordLoginUseCase,
    event_publisher: FakeDomainEventPublisher,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")
    with pytest.raises(AdminNotFoundException):
        use_case.execute(command)

    events = event_publisher.get_published_events_of_type(AdminLoginFailedEvent)
    assert len(events) == 1
    assert events[0].email == "nonexistent@lecoffre.com"
    assert events[0].reason == "User not found"


def test_should_store_admin_login_event_on_successful_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    admin_event_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)
    token_gateway.set_unique_jwt_part("uniqueness")

    command = AdminLoginCommand(email=email, password="secure123!")
    use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminLoginEvent"
    assert stored["actor_user_id"] == user_id


def test_should_store_admin_login_failed_event_on_wrong_password(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    admin_event_repository,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(secure123!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)

    command = AdminLoginCommand(email=email, password="wrong_password")
    with pytest.raises(InvalidCredentialsException):
        use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminLoginFailedEvent"
    assert stored["actor_user_id"] is None


def test_should_store_admin_login_failed_event_on_non_existent_admin(
    use_case: PasswordLoginUseCase,
    admin_event_repository,
):
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")
    with pytest.raises(AdminNotFoundException):
        use_case.execute(command)

    assert len(admin_event_repository.events) == 1
    stored = admin_event_repository.events[0]
    assert stored["event_type"] == "AdminLoginFailedEvent"
    assert stored["actor_user_id"] is None


def test_given_admin_user_when_logging_in_should_receive_token_with_admin_role(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    user_id = UUID("1a2b3c4d-0000-0000-0000-aabbccddeeff")
    email = "admin@lecoffre.com"
    password_hash = b"hashed(adminpass!)"

    user_password = UserPassword(id=user_id, email=email, password_hash=password_hash, display_name="Admin User")
    user_password_repository.save(user_password)
    user = User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")
    command = AdminLoginCommand(email=email, password="adminpass!")
    use_case.execute(command)

    assert token_gateway.last_generated_token is not None
    assert token_gateway.last_generated_token.roles == [ADMIN_ROLE]


def test_given_regular_user_when_logging_in_should_receive_token_with_empty_roles(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
):
    """
    Regression test: previously PasswordLoginUseCase (formerly AdminLoginUseCase) hardcoded roles=[ADMIN_ROLE] for
    every user. This meant a regular (non-admin) user would receive an admin JWT,
    allowing them to see all passwords. The fix looks up the user's actual roles.
    """
    user_id = UUID("deadbeef-1234-5678-abcd-000000000001")
    email = "user@lecoffre.com"
    password_hash = b"hashed(userpass!)"

    user_password = UserPassword(
        id=user_id,
        email=email,
        password_hash=password_hash,
        display_name="Regular User",
    )
    user_password_repository.save(user_password)
    user = User(id=user_id, username="regularuser", email=email, name="Regular User", roles=[])
    user_repository.save(user)

    token_gateway.set_unique_jwt_part("uniqueness")
    command = AdminLoginCommand(email=email, password="userpass!")
    use_case.execute(command)

    assert token_gateway.last_generated_token is not None
    assert token_gateway.last_generated_token.roles == []
    assert ADMIN_ROLE not in token_gateway.last_generated_token.roles


# ── Login-lockout behavior ────────────────────────────────────────────


def test_given_locked_email_when_logging_in_should_raise_account_locked_exception(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.force_lock(email, retry_after=42)

    command = AdminLoginCommand(email=email, password="secure123!")

    with pytest.raises(AccountLockedException) as excinfo:
        use_case.execute(command)

    assert excinfo.value.retry_after_seconds == 42


def test_given_locked_email_when_logging_in_should_not_call_password_verification(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    """Regression: the lockout gate runs before ``_lookup_and_verify`` so
    ``bcrypt.verify`` is never invoked during an active lockout. If this test
    fails, the locked-401 path's latency differs from the invalid-credentials
    path's — an account-enumeration oracle."""
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.force_lock(email, retry_after=10)
    assert password_hashing_gateway.get_verification_count() == 0

    with pytest.raises(AccountLockedException):
        use_case.execute(AdminLoginCommand(email=email, password="secure123!"))

    assert password_hashing_gateway.get_verification_count() == 0


def test_given_locked_email_when_logging_in_should_not_record_a_new_failed_login(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    """A locked attempt does not extend the lock — the gate short-circuits before
    the failure-recording branches in ``_lookup_and_verify`` can fire."""
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.force_lock(email, retry_after=30)

    with pytest.raises(AccountLockedException):
        use_case.execute(AdminLoginCommand(email=email, password="secure123!"))

    assert login_lockout_gateway.failed_login_calls == []
    assert login_lockout_gateway.successful_login_calls == []


# ── Constant-time password verification (timing-attack mitigation) ──────
#
# When a user is not found, we still call bcrypt.verify() with a pre-computed
# dummy hash to ensure constant-time response latency (~260ms) regardless of
# whether the email exists or not. This prevents timing oracles that could
# enumerate valid emails by measuring response time differences.


def test_given_nonexistent_email_should_call_hashing_gateway_verify_with_dummy_hash(
    use_case: PasswordLoginUseCase,
    password_hashing_gateway: FakePasswordHashingGateway,
):
    """When a user lookup returns None, verify() must still be called
    (with the dummy hash) to ensure constant-time latency. This test
    verifies the mitigation for AUTH-VULN-09 (timing oracle on /api/auth/login)."""
    from identity_access_management_context.application.use_cases.password_login_use_case import (
        DUMMY_PASSWORD_HASH,
    )

    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")

    with pytest.raises(AdminNotFoundException):
        use_case.execute(command)

    # verify() must have been called exactly once with the dummy hash
    assert password_hashing_gateway.get_verification_count() == 1
    assert password_hashing_gateway.get_last_verified_password() == "any_password"
    assert password_hashing_gateway.get_last_verified_hash() == DUMMY_PASSWORD_HASH, (
        "verify() must be called with DUMMY_PASSWORD_HASH to ensure timing is constant regardless of email existence"
    )


def test_given_nonexistent_email_should_still_raise_admin_not_found(
    use_case: PasswordLoginUseCase,
):
    """Even though verify() is called with a dummy hash, the behavior is identical:
    we still raise AdminNotFoundException. The dummy hash is never a valid match,
    so the exception is guaranteed regardless of the verify() result."""
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")

    with pytest.raises(AdminNotFoundException):
        use_case.execute(command)


def test_given_nonexistent_email_should_record_failed_login_after_dummy_verify(
    use_case: PasswordLoginUseCase,
    login_lockout_gateway: FakeLoginLockoutGateway,
):
    """Regression: even with the dummy verify() call, failed-login recording
    must still happen to support the lockout gateway's brute-force defense."""
    command = AdminLoginCommand(email="nonexistent@lecoffre.com", password="any_password")

    with pytest.raises(AdminNotFoundException):
        use_case.execute(command)

    assert login_lockout_gateway.failed_login_calls == ["nonexistent@lecoffre.com"]


# ── Lockout-gateway outage resilience ──────────────────────────────────
#
# These tests guard against a fail-open brute-force window when the lockout
# gateway can't record writes (SQL/Redis outage on a future adapter). The
# in-memory impl can't realistically raise, but the Protocol must be resilient
# the day a networked adapter lands — without these tests, a silent migration
# that breaks counter writes would let an attacker retry indefinitely because
# the counter never increments. The contract: a broken counter write does NOT
# change the user-visible 401 response (no enumeration oracle), does NOT
# swallow the original credential failure, and DOES surface an operator-visible
# log so SRE can correlate the lockout-store outage.


def test_given_record_failed_login_raises_when_credentials_are_wrong_should_still_raise_invalid_credentials(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    login_lockout_gateway: FakeLoginLockoutGateway,
    event_publisher: FakeDomainEventPublisher,
    admin_event_repository,
    caplog: pytest.LogCaptureFixture,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    login_lockout_gateway.make_record_failed_raise(RuntimeError("lockout store unreachable"))

    with caplog.at_level(
        "ERROR", logger="identity_access_management_context.application.use_cases.password_login_use_case"
    ):
        with pytest.raises(InvalidCredentialsException):
            use_case.execute(AdminLoginCommand(email=email, password="wrong_password"))

    # Audit trail must still be intact — event publishing happens before the
    # counter write, so a store outage doesn't cost forensic visibility.
    events = event_publisher.get_published_events_of_type(AdminLoginFailedEvent)
    assert len(events) == 1
    assert events[0].reason == "Invalid credentials"
    assert len(admin_event_repository.events) == 1
    # SRE signal: the counter outage surfaced at ERROR with exc_info so Sentry groups them.
    errors = [rec for rec in caplog.records if rec.levelname == "ERROR" and "lockout" in rec.getMessage().lower()]
    assert errors, "counter-write failure must log at ERROR so operators can see the outage"
    assert errors[0].exc_info is not None


def test_given_record_failed_login_raises_when_email_is_unknown_should_still_raise_admin_not_found(
    use_case: PasswordLoginUseCase,
    login_lockout_gateway: FakeLoginLockoutGateway,
    caplog: pytest.LogCaptureFixture,
):
    login_lockout_gateway.make_record_failed_raise(RuntimeError("lockout store unreachable"))

    with caplog.at_level(
        "ERROR", logger="identity_access_management_context.application.use_cases.password_login_use_case"
    ):
        with pytest.raises(AdminNotFoundException):
            use_case.execute(AdminLoginCommand(email="nobody@lecoffre.com", password="any"))

    errors = [rec for rec in caplog.records if rec.levelname == "ERROR" and "lockout" in rec.getMessage().lower()]
    assert errors, "counter-write failure must log at ERROR"


def test_given_record_successful_login_raises_when_credentials_are_correct_should_still_issue_tokens(
    use_case: PasswordLoginUseCase,
    user_password_repository: FakeUserPasswordRepository,
    user_repository: FakeUserRepository,
    token_gateway: FakeTokenGateway,
    login_lockout_gateway: FakeLoginLockoutGateway,
    caplog: pytest.LogCaptureFixture,
):
    """A counter-reset outage on a valid login must not deny the user access.
    The worst case is that a stale failure count carries over — future logins
    for this user will hit the lockout sooner than expected, which is the
    conservative direction. Denying tokens here would turn a counter-store
    outage into a full login outage for users with correct credentials."""
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "admin@lecoffre.com"
    user_password_repository.save(
        UserPassword(id=user_id, email=email, password_hash=b"hashed(secure123!)", display_name="Admin User"),
    )
    user_repository.save(User(id=user_id, username="admin", email=email, name="Admin User", roles=[ADMIN_ROLE]))
    token_gateway.set_unique_jwt_part("uniqueness")
    login_lockout_gateway.make_record_successful_raise(RuntimeError("lockout store unreachable"))

    with caplog.at_level(
        "ERROR", logger="identity_access_management_context.application.use_cases.password_login_use_case"
    ):
        response = use_case.execute(AdminLoginCommand(email=email, password="secure123!"))

    assert response.admin_id == user_id
    assert response.jwt_token
    errors = [rec for rec in caplog.records if rec.levelname == "ERROR" and "lockout" in rec.getMessage().lower()]
    assert errors, "counter-reset failure must log at ERROR"
