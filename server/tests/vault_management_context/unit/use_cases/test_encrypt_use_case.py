import pytest

from vault_management_context.application.commands import EncryptCommand
from vault_management_context.application.use_cases import (
    EncryptUseCase,
)

from ..fakes import FakeEncryptionGateway, FakeVaultSessionGateway


@pytest.fixture
def use_case(
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
):
    return EncryptUseCase(encryption_gateway, vault_session_gateway)


def test_given_decrypted_data_when_encrypting_should_return_encrypted_data(
    use_case,
    encryption_gateway: FakeEncryptionGateway,
    vault_session_gateway: FakeVaultSessionGateway,
):
    master_key = "master_key"
    decrypted = "plain_test_data"
    encrypted = "encrypted_test_data"

    encryption_gateway.set_encrypted_data(encrypted)
    encryption_gateway.set_decrypted_data(decrypted)
    encryption_gateway.set_master_key(master_key)
    vault_session_gateway.store_decrypted_key("master_key")

    command = EncryptCommand(decrypted_data=decrypted)
    result = use_case.execute(command)

    assert result == encrypted
