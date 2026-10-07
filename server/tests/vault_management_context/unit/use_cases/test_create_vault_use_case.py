import hashlib
from datetime import timedelta
from uuid import uuid4

import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from tests.shared_kernel.fakes import FakeTransactionGateway
from vault_management_context.application.commands import CreateVaultCommand
from vault_management_context.application.responses.vault_status import VaultStatus
from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
)
from vault_management_context.domain.entities import Share, Vault
from vault_management_context.domain.events import VaultCreatedEvent
from vault_management_context.domain.exceptions import (
    InvalidShareCountError,
    InvalidThresholdError,
    ThresholdExceedsShareCountError,
    VaultAlreadyExistsError,
)
from vault_management_context.domain.value_objects.shamir_result import ShamirResult

from ..fakes import (
    FakeEncryptionGateway,
    FakeShamirGateway,
    FakeShareLinkRepository,
    FakeShareSealingGateway,
    FakeVaultRepository,
    FakeVaultSessionGateway,
)


@pytest.fixture()
def use_case(
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
    event_publisher,
    vault_event_repository,
    share_link_repository,
    share_sealing_gateway,
    time_gateway,
    transaction_gateway,
):
    return CreateVaultUseCase(
        vault_repository,
        shamir_gateway,
        encryption_gateway,
        vault_session_gateway,
        event_publisher,
        vault_event_repository,
        share_link_repository,
        share_sealing_gateway,
        time_gateway,
        transaction_gateway,
    )


def _configure_setup(shamir_gateway, encryption_gateway, shares: list[Share]) -> None:
    master_key = "master_secret_from_shamir"
    shamir_gateway.set_shamir_result(ShamirResult(shares=shares, master_key=master_key))
    encryption_gateway.set_encrypted_data("encrypted_vault_key_123")
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")


def test_given_valid_vault_config_when_creating_vault_should_create_shares_and_store_encrypted_key(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
):
    expected_shares = [
        Share("1"),
        Share("2"),
        Share("3"),
        Share("4"),
        Share("5"),
    ]
    master_key = "master_secret_from_shamir"
    encrypted_key = "encrypted_vault_key_123"
    setup_id = uuid4()

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)

    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")  # For decrypt_and_store_key

    command = CreateVaultCommand(nb_shares=5, threshold=3, setup_id=setup_id)
    result = use_case.execute(command)

    assert result.setup_id == str(setup_id)
    assert [link.share_index for link in result.share_links] == [1, 2, 3, 4, 5]

    stored_vault = vault_repository.get()

    assert stored_vault
    assert stored_vault.nb_shares == 5
    assert stored_vault.threshold == 3
    assert stored_vault.encrypted_key == encrypted_key
    assert stored_vault.status == VaultStatus.PENDING.value
    assert stored_vault.setup_id == str(setup_id)


def test_given_existing_validated_vault_when_creating_vault_should_raise_vault_already_exists_error(
    use_case, vault_repository: FakeVaultRepository
):
    # Create a vault that is already validated (not in PENDING state)
    vault_repository.save(
        Vault(
            nb_shares=5,
            threshold=3,
            encrypted_key="test",
            setup_id=str(uuid4()),
            status=VaultStatus.SETUPED.value,
        )
    )

    command = CreateVaultCommand(nb_shares=5, threshold=3, setup_id=uuid4())
    with pytest.raises(VaultAlreadyExistsError) as exc_info:
        use_case.execute(command)

    assert str(exc_info.value) == "A vault has already been created for this organization"


def test_given_pending_vault_when_creating_vault_should_allow_re_setup(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
):
    # Create a vault in PENDING state
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key="test",
            status=VaultStatus.PENDING.value,
            setup_id=str(uuid4()),
        )
    )

    expected_shares = [Share("1"), Share("2")]
    master_key = "master_secret_from_shamir"
    encrypted_key = "encrypted_vault_key_123"
    new_setup_id = uuid4()

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")  # For decrypt_and_store_key

    # Should be able to re-setup
    command = CreateVaultCommand(nb_shares=2, threshold=2, setup_id=new_setup_id)
    result = use_case.execute(command)
    assert len(result.share_links) == len(expected_shares)
    assert result.setup_id == str(new_setup_id)


def test_given_nb_shares_less_than_2_when_creating_vault_should_raise_invalid_share_count_error(
    use_case,
):
    command = CreateVaultCommand(nb_shares=1, threshold=2, setup_id=uuid4())
    with pytest.raises(InvalidShareCountError) as exc_info:
        use_case.execute(command)

    assert str(exc_info.value) == "Share count must be at least 2 for security reasons, got 1"


def test_given_threshold_less_than_2_when_creating_vault_should_raise_invalid_threshold_error(
    use_case,
):
    command = CreateVaultCommand(nb_shares=3, threshold=1, setup_id=uuid4())
    with pytest.raises(InvalidThresholdError) as exc_info:
        use_case.execute(command)

    assert str(exc_info.value) == "Threshold must be at least 2 to ensure security, got 1"


def test_given_threshold_greater_than_nb_shares_when_creating_vault_should_raise_threshold_exceeds_error(
    use_case,
):
    command = CreateVaultCommand(nb_shares=3, threshold=4, setup_id=uuid4())
    with pytest.raises(ThresholdExceedsShareCountError) as exc_info:
        use_case.execute(command)

    expected_message = "Threshold 4 cannot exceed share count 3 - impossible to unlock vault"
    assert str(exc_info.value) == expected_message


def test_given_valid_vault_config_when_creating_vault_should_publish_vault_created_event(
    use_case,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    expected_shares = [Share("1"), Share("2"), Share("3"), Share("4"), Share("5")]
    master_key = "master_secret_from_shamir"
    encrypted_key = "encrypted_vault_key_123"
    setup_id = uuid4()

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")

    command = CreateVaultCommand(nb_shares=5, threshold=3, setup_id=setup_id)
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(VaultCreatedEvent)
    assert len(events) == 1
    assert events[0].setup_id == str(setup_id)
    assert events[0].nb_shares == 5
    assert events[0].threshold == 3


def test_given_valid_vault_config_when_creating_vault_should_store_vault_created_event(
    use_case,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_event_repository,
):
    expected_shares = [Share("1"), Share("2"), Share("3"), Share("4"), Share("5")]
    master_key = "master_secret_from_shamir"
    encrypted_key = "encrypted_vault_key_123"
    setup_id = uuid4()

    shamir_result = ShamirResult(shares=expected_shares, master_key=master_key)
    shamir_gateway.set_shamir_result(shamir_result)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)
    encryption_gateway.set_decrypted_data("decrypted_vault_key")

    command = CreateVaultCommand(nb_shares=5, threshold=3, setup_id=setup_id)
    use_case.execute(command)

    assert len(vault_event_repository.events) == 1
    stored = vault_event_repository.events[0]
    assert stored["event_type"] == "VaultCreatedEvent"
    assert stored["actor_user_id"] is None


def test_given_valid_vault_config_when_creating_vault_should_never_return_shares_in_clear(
    use_case, shamir_gateway, encryption_gateway
):
    shares = [Share("1:aaaa"), Share("2:bbbb"), Share("3:cccc")]
    _configure_setup(shamir_gateway, encryption_gateway, shares)

    result = use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=uuid4()))

    assert not hasattr(result, "shares")
    returned = repr(result) + "".join(link.token for link in result.share_links)
    for share in shares:
        assert share.secret not in returned


def test_given_valid_vault_config_when_creating_vault_should_issue_one_link_per_share_valid_48_hours(
    use_case, shamir_gateway, encryption_gateway, time_gateway
):
    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:aa"), Share("2:bb"), Share("3:cc")])

    result = use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=uuid4()))

    assert len(result.share_links) == 3
    assert len({link.token for link in result.share_links}) == 3
    expected_expiry = time_gateway.get_current_time() + timedelta(hours=48)
    assert all(link.expires_at == expected_expiry for link in result.share_links)


def test_given_valid_vault_config_when_creating_vault_should_store_each_share_sealed_under_its_own_token(
    use_case,
    shamir_gateway,
    encryption_gateway,
    share_link_repository: FakeShareLinkRepository,
    share_sealing_gateway: FakeShareSealingGateway,
):
    shares = [Share("1:aa"), Share("2:bb"), Share("3:cc")]
    _configure_setup(shamir_gateway, encryption_gateway, shares)
    setup_id = uuid4()

    result = use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=setup_id))

    # Every share was sealed exactly once, each under the token handed out for it.
    assert [share for share, _ in share_sealing_gateway.sealed] == shares
    assert [token.value for _, token in share_sealing_gateway.sealed] == [link.token for link in result.share_links]

    stored = share_link_repository.stored()
    assert [link.share_index for link in stored] == [1, 2, 3]
    for stored_link, issued, share in zip(stored, result.share_links, shares, strict=True):
        # Only the hash of the token is stored, never the token itself.
        assert stored_link.lookup_hash == hashlib.sha256(issued.token.encode()).hexdigest()
        assert issued.token not in repr(stored_link)
        # Bound to the setup and the index it is handed out with
        assert stored_link.sealed_share == (
            f"sealed[{share.secret}]by[{stored_link.lookup_hash}]as[{setup_id}#{stored_link.share_index}]"
        )
        assert stored_link.ack_hash == f"ack-hash[{stored_link.lookup_hash}]"
        assert stored_link.delivered_at is None
        assert stored_link.setup_id == str(setup_id)


def test_given_pending_vault_when_re_setting_up_should_replace_the_previous_share_links(
    use_case, shamir_gateway, encryption_gateway, share_link_repository: FakeShareLinkRepository
):
    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:aa"), Share("2:bb"), Share("3:cc")])
    use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=uuid4()))

    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:dd"), Share("2:ee")])
    second_setup_id = uuid4()
    second = use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=second_setup_id))

    stored = share_link_repository.stored()
    assert len(stored) == 2
    assert {link.setup_id for link in stored} == {str(second_setup_id)}
    assert {link.lookup_hash for link in stored} == {
        hashlib.sha256(link.token.encode()).hexdigest() for link in second.share_links
    }


def test_given_existing_validated_vault_when_creating_vault_should_leave_share_links_untouched(
    use_case, vault_repository: FakeVaultRepository, share_link_repository: FakeShareLinkRepository
):
    vault_repository.save(
        Vault(nb_shares=3, threshold=2, encrypted_key="k", setup_id="old", status=VaultStatus.SETUPED.value)
    )

    with pytest.raises(VaultAlreadyExistsError):
        use_case.execute(CreateVaultCommand(nb_shares=3, threshold=2, setup_id=uuid4()))

    assert share_link_repository.stored() == []


def test_given_invalid_config_when_creating_vault_should_not_issue_any_link(
    use_case, share_link_repository: FakeShareLinkRepository
):
    with pytest.raises(ThresholdExceedsShareCountError):
        use_case.execute(CreateVaultCommand(nb_shares=2, threshold=3, setup_id=uuid4()))

    assert share_link_repository.stored() == []


def test_given_valid_vault_config_when_creating_vault_should_commit_the_setup_once(
    use_case, shamir_gateway, encryption_gateway, transaction_gateway: FakeTransactionGateway
):
    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:aa"), Share("2:bb")])

    use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=uuid4()))

    assert transaction_gateway.committed == 1
    assert transaction_gateway.rolled_back == 0


def test_given_sealing_fails_when_creating_vault_should_roll_back_and_keep_the_key_out_of_memory(
    use_case,
    shamir_gateway,
    encryption_gateway,
    share_sealing_gateway: FakeShareSealingGateway,
    transaction_gateway: FakeTransactionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:aa"), Share("2:bb")])
    share_sealing_gateway.error = RuntimeError("sealing failed")

    with pytest.raises(RuntimeError):
        use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=uuid4()))

    assert transaction_gateway.rolled_back == 1
    assert transaction_gateway.committed == 0
    assert vault_session_gateway.is_vault_locked()
    assert event_publisher.get_published_events_of_type(VaultCreatedEvent) == []


def test_given_commit_fails_when_creating_vault_should_keep_the_key_out_of_memory(
    use_case,
    shamir_gateway,
    encryption_gateway,
    transaction_gateway: FakeTransactionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:aa"), Share("2:bb")])
    transaction_gateway.commit_error = RuntimeError("commit failed")

    with pytest.raises(RuntimeError):
        use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=uuid4()))

    assert vault_session_gateway.is_vault_locked()
    assert event_publisher.get_published_events_of_type(VaultCreatedEvent) == []


def test_given_pending_vault_when_re_setup_fails_should_keep_the_previous_key_in_memory(
    use_case,
    shamir_gateway,
    encryption_gateway,
    share_sealing_gateway: FakeShareSealingGateway,
    vault_session_gateway: FakeVaultSessionGateway,
):
    # The rollback leaves the earlier setup in the database, so the key in
    # memory must still be the one that matches it.
    _configure_setup(shamir_gateway, encryption_gateway, [Share("1:aa"), Share("2:bb")])
    use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=uuid4()))

    encryption_gateway.set_decrypted_data("key_of_the_failed_setup")
    share_sealing_gateway.error = RuntimeError("sealing failed")
    with pytest.raises(RuntimeError):
        use_case.execute(CreateVaultCommand(nb_shares=2, threshold=2, setup_id=uuid4()))

    assert vault_session_gateway.get_decrypted_key() == "decrypted_vault_key"
