from unittest.mock import Mock

import pytest

from identity_access_management_context.adapters.secondary.private_api import (
    PrivateApiSsoEncryptionGateway,
)


@pytest.fixture
def mock_encryption_api():
    """Mock EncryptionApi from vault management context"""
    return Mock()


@pytest.fixture
def private_api_sso_encryption_gateway(mock_encryption_api):
    """Fixture providing the gateway wrapped around mocked encryption API"""
    return PrivateApiSsoEncryptionGateway(mock_encryption_api)


def test_should_encrypt_plaintext(private_api_sso_encryption_gateway, mock_encryption_api):
    # Arrange
    plaintext = "client_secret_value"
    expected_encrypted = "encrypted_secret_xyz"
    mock_encryption_api.encrypt.return_value = expected_encrypted

    # Act
    encrypted = private_api_sso_encryption_gateway.encrypt(plaintext)

    # Assert
    assert encrypted == expected_encrypted
    mock_encryption_api.encrypt.assert_called_once_with(plaintext)


def test_should_decrypt_ciphertext(private_api_sso_encryption_gateway, mock_encryption_api):
    # Arrange
    ciphertext = "encrypted_secret_xyz"
    expected_plaintext = "client_secret_value"
    mock_encryption_api.decrypt.return_value = expected_plaintext

    # Act
    decrypted = private_api_sso_encryption_gateway.decrypt(ciphertext)

    # Assert
    assert decrypted == expected_plaintext
    mock_encryption_api.decrypt.assert_called_once_with(ciphertext)


def test_should_return_original_data_when_encrypt_then_decrypt(private_api_sso_encryption_gateway, mock_encryption_api):
    # Arrange
    original_data = "sso_client_secret_123!@#"
    encrypted_value = "encrypted_xyz_abc"

    mock_encryption_api.encrypt.return_value = encrypted_value
    mock_encryption_api.decrypt.return_value = original_data

    # Act
    encrypted = private_api_sso_encryption_gateway.encrypt(original_data)
    decrypted = private_api_sso_encryption_gateway.decrypt(encrypted)

    # Assert
    assert decrypted == original_data
    assert encrypted == encrypted_value
    mock_encryption_api.encrypt.assert_called_once_with(original_data)
    mock_encryption_api.decrypt.assert_called_once_with(encrypted_value)


def test_should_produce_different_ciphertexts_when_encrypting_different_data(
    private_api_sso_encryption_gateway, mock_encryption_api
):
    # Arrange
    data1 = "secret_one"
    data2 = "secret_two"
    encrypted1_value = "encrypted_one"
    encrypted2_value = "encrypted_two"

    mock_encryption_api.encrypt.side_effect = [encrypted1_value, encrypted2_value]

    # Act
    encrypted1 = private_api_sso_encryption_gateway.encrypt(data1)
    encrypted2 = private_api_sso_encryption_gateway.encrypt(data2)

    # Assert
    assert encrypted1 == encrypted1_value
    assert encrypted2 == encrypted2_value
    assert encrypted1 != encrypted2
    assert mock_encryption_api.encrypt.call_count == 2
