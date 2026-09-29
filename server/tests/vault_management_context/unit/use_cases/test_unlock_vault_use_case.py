import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from vault_management_context.application.commands import UnlockVaultCommand
from vault_management_context.application.responses import VaultStatus
from vault_management_context.application.use_cases import (
    UnlockVaultUseCase,
)
from vault_management_context.domain.entities import Share, Vault
from vault_management_context.domain.events import VaultUnlockedEvent
from vault_management_context.domain.exceptions import (
    ShareReconstructionError,
    VaultNotSetupException,
    VaultUnlockedError,
)
from vault_management_context.domain.value_objects import ShamirResult, UnlockSessionId

from ..fakes import (
    FakeEncryptionGateway,
    FakeShamirGateway,
    FakeShareRepository,
    FakeVaultRepository,
    FakeVaultSessionGateway,
)

SESSION = UnlockSessionId("SESSIONAAAAAAAAA")
OTHER_SESSION = UnlockSessionId("SESSIONBBBBBBBBB")


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

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)
    use_case.execute(command)

    # Verify the decrypted key is now in session
    decrypted_key = vault_session_gateway.get_decrypted_key()
    assert decrypted_key == vault_key


def test_given_vault_not_setup_when_unlocking_vault_should_raise_vault_not_setup_exception(
    use_case,
):
    shares = [Share("share0"), Share("share1")]

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)
    with pytest.raises(VaultNotSetupException):
        use_case.execute(command)


def test_given_insufficient_shares_when_unlocking_vault_should_raise_share_reconstruction_error(
    use_case, vault_repository
):
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    shares = [Share("share0")]

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)
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

    command = UnlockVaultCommand(session_id=SESSION, shares=invalid_shares)
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

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)
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
    share_repository.add(SESSION, old_shares)

    combined_shares = old_shares + new_shares
    shamir_gateway.set_shamir_result(ShamirResult(combined_shares, master_key))
    encryption_gateway.set_decrypted_data(vault_key)
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    command = UnlockVaultCommand(session_id=SESSION, shares=new_shares)
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

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)
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

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)

    with pytest.raises(ShareReconstructionError):
        use_case.execute(command)

    stored_shares = share_repository.get_all(SESSION)
    assert len(stored_shares) == 1
    assert stored_shares[0].secret == "share0"


def test_given_duplicate_share_when_unlocking_should_not_count_it_twice(
    use_case,
    vault_repository: FakeVaultRepository,
    share_repository: FakeShareRepository,
):
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    share_repository.add(SESSION, [Share("0:aa")])  # already pending

    # Resubmit the already-pending share plus a new one; reconstruction fails
    # (no shamir result configured), so the deduped new share is stored.
    with pytest.raises(ShareReconstructionError):
        use_case.execute(UnlockVaultCommand(session_id=SESSION, shares=[Share("0:aa"), Share("1:bb")]))

    assert sorted(s.secret for s in share_repository.get_all(SESSION)) == ["0:aa", "1:bb"]

    # Resubmitting only the duplicate adds nothing.
    with pytest.raises(ShareReconstructionError):
        use_case.execute(UnlockVaultCommand(session_id=SESSION, shares=[Share("0:aa")]))

    assert len(share_repository.get_all(SESSION)) == 2


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

    command = UnlockVaultCommand(session_id=SESSION, shares=shares)
    use_case.execute(command)

    assert len(vault_event_repository.events) == 1
    stored = vault_event_repository.events[0]
    assert stored["event_type"] == "VaultUnlockedEvent"
    assert stored["actor_user_id"] is None


def test_given_shares_pending_in_another_session_when_unlocking_should_not_use_them(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    share_repository: FakeShareRepository,
):
    encrypted_key = "encrypted_vault_key_hex"
    master_key = "master_key"
    vault_repository.save(
        Vault(
            nb_shares=3,
            threshold=2,
            encrypted_key=encrypted_key,
            setup_id="test-setup-id",
            status=VaultStatus.SETUPED.value,
        )
    )
    share_repository.add(OTHER_SESSION, [Share("share0")])
    shamir_gateway.set_shamir_result(ShamirResult([Share("share0"), Share("share1")], master_key))
    encryption_gateway.set_decrypted_data("test_vault_key_12345678")
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    with pytest.raises(ShareReconstructionError):
        use_case.execute(UnlockVaultCommand(session_id=SESSION, shares=[Share("share1")]))

    assert [s.secret for s in share_repository.get_all(SESSION)] == ["share1"]
    assert [s.secret for s in share_repository.get_all(OTHER_SESSION)] == ["share0"]


def test_given_valid_shares_when_unlocking_vault_should_clear_pending_shares_of_every_session(
    use_case,
    vault_repository: FakeVaultRepository,
    shamir_gateway: FakeShamirGateway,
    encryption_gateway: FakeEncryptionGateway,
    share_repository: FakeShareRepository,
):
    encrypted_key = "encrypted_vault_key_hex"
    master_key = "master_key"
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
    share_repository.add(SESSION, [Share("share0")])
    share_repository.add(OTHER_SESSION, [Share("stale")])
    shamir_gateway.set_shamir_result(ShamirResult(shares, master_key))
    encryption_gateway.set_decrypted_data("test_vault_key_12345678")
    encryption_gateway.set_encrypted_data(encrypted_key)
    encryption_gateway.set_master_key(master_key)

    use_case.execute(UnlockVaultCommand(session_id=SESSION, shares=[Share("share1")]))

    assert share_repository.get_all(SESSION) == []
    assert share_repository.get_all(OTHER_SESSION) == []


def test_given_session_holding_as_many_shares_as_the_vault_when_adding_more_should_drop_them(
    use_case,
    vault_repository: FakeVaultRepository,
    share_repository: FakeShareRepository,
):
    # Reconstruction fails (no shamir result configured): shares are stored, up to nb_shares.
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    share_repository.add(SESSION, [Share("0:aa"), Share("1:bb")])

    with pytest.raises(ShareReconstructionError):
        use_case.execute(UnlockVaultCommand(session_id=SESSION, shares=[Share("2:cc"), Share("3:dd")]))
    with pytest.raises(ShareReconstructionError):
        use_case.execute(UnlockVaultCommand(session_id=SESSION, shares=[Share("4:ee")]))

    assert [s.secret for s in share_repository.get_all(SESSION)] == ["0:aa", "1:bb", "2:cc"]
