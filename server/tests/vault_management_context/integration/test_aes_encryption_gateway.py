import pytest

from vault_management_context.adapters.secondary.gateways import AesEncryptionGateway


@pytest.fixture
def aes_encryption():
    return AesEncryptionGateway()


def test_encrypting_aes_can_decrypt_with_same_key(aes_encryption: AesEncryptionGateway):
    vault_key = aes_encryption.generate_vault_key("my_master_key_123")
    plaintext = "Hello, World!"

    encrypted = aes_encryption.encrypt(plaintext, vault_key)
    decrypted = aes_encryption.decrypt(encrypted, vault_key)

    assert decrypted == plaintext
