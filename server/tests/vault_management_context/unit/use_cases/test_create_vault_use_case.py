import pytest
from uuid import uuid4

from ..fakes import (
    FakeVaultRepository,
    FakeShamirGateway,
    FakeEncryptionGateway,
    FakeVaultSessionGateway,
)
from vault_management_context.application.commands import CreateVaultCommand
from vault_management_context.domain.entities import Vault, Share
from vault_management_context.application.responses.vault_status import VaultStatus
from vault_management_context.domain.exceptions import (
    VaultAlreadyExistsError,
    InvalidShareCountError,
    InvalidThresholdError,
    ThresholdExceedsShareCountError,
)
from vault_management_context.application.use_cases import (
    CreateVaultUseCase,
)
from vault_management_context.domain.value_objects.shamir_result import ShamirResult
from vault_management_context.domain.events import VaultCreatedEvent
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher


@pytest.fixture()
def use_case(
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
    event_publisher,
):
    return CreateVaultUseCase(
        vault_repository, shamir_gateway, encryption_gateway, vault_session_gateway, event_publisher
    )


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
    encryption_gateway.set_decrypted_data(
        "decrypted_vault_key"
    )  # For decrypt_and_store_key

    command = CreateVaultCommand(nb_shares=5, threshold=3, setup_id=setup_id)
    result = use_case.execute(command)

    # Check that result is VaultSetupResponse with setup_id and shares
    assert result.shares == expected_shares
    assert result.setup_id == str(setup_id)

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

    assert (
        str(exc_info.value) == "A vault has already been created for this organization"
    )


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
    encryption_gateway.set_decrypted_data(
        "decrypted_vault_key"
    )  # For decrypt_and_store_key

    # Should be able to re-setup
    command = CreateVaultCommand(nb_shares=2, threshold=2, setup_id=new_setup_id)
    result = use_case.execute(command)
    assert result.shares == expected_shares
    assert result.setup_id == str(new_setup_id)


def test_given_nb_shares_less_than_2_when_creating_vault_should_raise_invalid_share_count_error(
    use_case,
):
    command = CreateVaultCommand(nb_shares=1, threshold=2, setup_id=uuid4())
    with pytest.raises(InvalidShareCountError) as exc_info:
        use_case.execute(command)

    assert (
        str(exc_info.value)
        == "Share count must be at least 2 for security reasons, got 1"
    )


def test_given_threshold_less_than_2_when_creating_vault_should_raise_invalid_threshold_error(
    use_case,
):
    command = CreateVaultCommand(nb_shares=3, threshold=1, setup_id=uuid4())
    with pytest.raises(InvalidThresholdError) as exc_info:
        use_case.execute(command)

    assert (
        str(exc_info.value) == "Threshold must be at least 2 to ensure security, got 1"
    )


def test_given_threshold_greater_than_nb_shares_when_creating_vault_should_raise_threshold_exceeds_error(
    use_case,
):
    command = CreateVaultCommand(nb_shares=3, threshold=4, setup_id=uuid4())
    with pytest.raises(ThresholdExceedsShareCountError) as exc_info:
        use_case.execute(command)

    expected_message = (
        "Threshold 4 cannot exceed share count 3 - impossible to unlock vault"
    )
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
