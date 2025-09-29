import pytest

from vault_management_context.application.use_cases import (
    EncryptUseCase,
)


@pytest.fixture
def use_case(encryption_gateway, vault_session_gateway):
    return EncryptUseCase(encryption_gateway, vault_session_gateway)


def test_should_encrypt_data(use_case, encryption_gateway, vault_session_gateway):
    master_key = "master_key"
    decrypted = "plain_test_data"
    encrypted = "encrypted_test_data"

    encryption_gateway.set_encrypted_data(encrypted)
    encryption_gateway.set_decrypted_data(decrypted)
    encryption_gateway.set_master_key(master_key)
    vault_session_gateway.store_decrypted_key("master_key")

    result = use_case.execute(decrypted)

    assert result == encrypted
