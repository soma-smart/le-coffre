import pytest

from vault_management_context.application.commands import UnlockVaultCommand
from vault_management_context.application.responses import VaultStatus
from vault_management_context.domain.entities import Share, Vault
from vault_management_context.domain.value_objects import ShamirResult
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    ShareReconstructionError,
    VaultUnlockedError,
)
from vault_management_context.application.use_cases import (
    UnlockVaultUseCase,
)
from vault_management_context.domain.events import VaultUnlockedEvent
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import (
    FakeVaultRepository,
    FakeShamirGateway,
    FakeEncryptionGateway,
    FakeVaultSessionGateway,
    FakeShareRepository,
)


@pytest.fixture()
def use_case(
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
    share_repository: FakeShareRepository,
    event_publisher,
    vault_event_repository,
):
    return UnlockVaultUseCase(
        vault_repository,
        shamir_gateway,
        encryption_gateway,
        vault_session_gateway,
        share_repository,
        event_publisher,
        vault_event_repository,
    )


def test_given_valid_shares_when_unlocking_vault_should_decrypt_and_store_key(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
):
    vault_key = "test_vault_key_12345678"
    master_key = "master_key"
    encrypted_key = "encrypted_vault_key_hex"
    shares = [Share("share0"), Share("share1")]

    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    command = UnlockVaultCommand(shares=shares)
    use_case.execute(command)

    # Verify the decrypted key is now in session
    decrypted_key = vault_session_gateway.get_decrypted_key()
    assert decrypted_key == vault_key


def test_given_vault_not_setup_when_unlocking_vault_should_raise_vault_not_setup_exception(
    use_case,
):
    shares = [Share("share0"), Share("share1")]

    command = UnlockVaultCommand(shares=shares)
    with pytest.raises(VaultNotSetupException):
        use_case.execute(command)


def test_given_insufficient_shares_when_unlocking_vault_should_raise_share_reconstruction_error(
    use_case, vault_repository
):
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    shares = [Share("share0")]

    command = UnlockVaultCommand(shares=shares)
    with pytest.raises(ShareReconstructionError):
        use_case.execute(command)


def test_given_invalid_shares_when_unlocking_vault_should_raise_share_reconstruction_error(
    use_case, vault_repository: FakeVaultRepository, shamir_gateway: FakeShamirGateway
):
    encrypted_key = "encrypted_vault_key_hex"
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shares = [Share("share0"), Share("share1")]
    master_secret = "master_secret"
    shamir_gateway.set_shamir_result(ShamirResult(shares, master_secret))

    invalid_shares = [Share("invalid_share0"), Share("invalid_share1")]

    command = UnlockVaultCommand(shares=invalid_shares)
    with pytest.raises(ShareReconstructionError):
        use_case.execute(command)


def test_given_already_unlocked_vault_when_unlocking_vault_should_raise_vault_unlocked_error(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
):
    encrypted_key = "encrypted_vault_key_hex"
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shares = [Share("share0"), Share("share1")]
    master_key = "master_key"
    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))

    vault_key = "test_vault_key_12345678"
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    command = UnlockVaultCommand(shares=shares)
    use_case.execute(command)

    with pytest.raises(VaultUnlockedError):
        use_case.execute(command)


def test_given_existing_shares_when_unlocking_vault_should_combine_shares(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
    share_repository: FakeShareRepository,
):
    vault_key = "test_vault_key_12345678"
    master_key = "master_key"
    encrypted_key = "encrypted_vault_key_hex"
    new_shares = [Share("share1")]

    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    old_shares = [Share("share0")]
    share_repository.add(old_shares)

    combined_shares = old_shares + new_shares
    shamir_gateway.set_shamir_result(ShamirResult(combined_shares, master_key))
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    command = UnlockVaultCommand(shares=new_shares)
    use_case.execute(command)

    decrypted_key = vault_session_gateway.get_decrypted_key()
    assert decrypted_key == vault_key


def test_given_valid_shares_when_unlocking_vault_should_publish_vault_unlocked_event(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    event_publisher: FakeDomainEventPublisher,
):
    vault_key = "test_vault_key_12345678"
    master_key = "master_key"
    encrypted_key = "encrypted_vault_key_hex"
    shares = [Share("share0"), Share("share1")]

    vault_repository.save(
        Vault(
            nb_shares=3, threshold=2, encrypted_key=encrypted_key,
            setup_id="test-setup-id", status=VaultStatus.SETUPED.value,
        )
    )

    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    command = UnlockVaultCommand(shares=shares)
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(VaultUnlockedEvent)
    assert len(events) == 1


def test_given_insufficient_shares_when_unlocking_fails_should_add_shares_to_repository(
    use_case,
    vault_repository: FakeVaultRepository,
    share_repository: FakeShareRepository,
):
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key="encrypted_vault_key_hex",
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shares = [Share("share0")]

    command = UnlockVaultCommand(shares=shares)

    with pytest.raises(ShareReconstructionError):
        use_case.execute(command)

    stored_shares = share_repository.get_all()
    assert len(stored_shares) == 1
    assert stored_shares[0].secret == "share0"


def test_given_valid_shares_when_unlocking_vault_should_store_vault_unlocked_event(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    vault_event_repository,
):
    vault_key = "test_vault_key_12345678"
    master_key = "master_key"
    encrypted_key = "encrypted_vault_key_hex"
    shares = [Share("share0"), Share("share1")]

    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )

    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    command = UnlockVaultCommand(shares=shares)
    use_case.execute(command)

    assert len(vault_event_repository.events) == 1
    stored = vault_event_repository.events[0]
    assert stored["event_type"] == "VaultUnlockedEvent"
    assert stored["actor_user_id"] is None
