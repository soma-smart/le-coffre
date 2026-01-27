import pytest
from unittest.mock import Mock

from password_management_context.adapters.secondary.private_api import (
    PrivateApiPasswordEncryptionGateway,
)


@pytest.fixture
def mock_encryption_api():
    """Mock EncryptionApi from vault management context"""
    return Mock()


@pytest.fixture
def private_api_password_encryption_gateway(mock_encryption_api):
    """Fixture providing the gateway wrapped around mocked encryption API"""
    return PrivateApiPasswordEncryptionGateway(mock_encryption_api)


def test_should_encrypt_plaintext_password(
    private_api_password_encryption_gateway, mock_encryption_api
):
    # Arrange
    plaintext = "my_super_secret_password"
    expected_encrypted = "encrypted_data_xyz"
    mock_encryption_api.encrypt.return_value = expected_encrypted

    # Act
    encrypted = private_api_password_encryption_gateway.encrypt(plaintext)

    # Assert
    assert encrypted == expected_encrypted
    mock_encryption_api.encrypt.assert_called_once_with(plaintext)


def test_should_decrypt_ciphertext(
    private_api_password_encryption_gateway, mock_encryption_api
):
    # Arrange
    ciphertext = "encrypted_data_xyz"
    expected_plaintext = "my_super_secret_password"
    mock_encryption_api.decrypt.return_value = expected_plaintext

    # Act
    decrypted = private_api_password_encryption_gateway.decrypt(ciphertext)

    # Assert
    assert decrypted == expected_plaintext
    mock_encryption_api.decrypt.assert_called_once_with(ciphertext)


def test_should_return_original_password_when_encrypt_then_decrypt(
    private_api_password_encryption_gateway, mock_encryption_api
):
    # Arrange
    original_password = "test_password_123!@#"
    encrypted_value = "encrypted_xyz_abc"

    mock_encryption_api.encrypt.return_value = encrypted_value
    mock_encryption_api.decrypt.return_value = original_password

    # Act
    encrypted = private_api_password_encryption_gateway.encrypt(original_password)
    decrypted = private_api_password_encryption_gateway.decrypt(encrypted)

    # Assert
    assert decrypted == original_password
    assert encrypted == encrypted_value
    mock_encryption_api.encrypt.assert_called_once_with(original_password)
    mock_encryption_api.decrypt.assert_called_once_with(encrypted_value)


def test_should_produce_different_ciphertexts_when_encrypting_different_passwords(
    private_api_password_encryption_gateway, mock_encryption_api
):
    # Arrange
    password1 = "password_one"
    password2 = "password_two"
    encrypted1_value = "encrypted_one"
    encrypted2_value = "encrypted_two"

    mock_encryption_api.encrypt.side_effect = [encrypted1_value, encrypted2_value]

    # Act
    encrypted1 = private_api_password_encryption_gateway.encrypt(password1)
    encrypted2 = private_api_password_encryption_gateway.encrypt(password2)

    # Assert
    assert encrypted1 == encrypted1_value
    assert encrypted2 == encrypted2_value
    assert encrypted1 != encrypted2
    assert mock_encryption_api.encrypt.call_count == 2
