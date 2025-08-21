import pytest

from vault_management_context.application.use_cases import (
    EncryptUseCase,
    DecryptUseCase,
)


@pytest.fixture
def context(encryption_gateway, vault_session_gateway):
    return {
        "encrypt_use_case": EncryptUseCase(encryption_gateway, vault_session_gateway),
        "decrypt_use_case": DecryptUseCase(encryption_gateway, vault_session_gateway),
    }


def test_should_decrypt_an_encrypted_message(e2e_client, context):
    response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )

    encrypted_message = context["encrypt_use_case"].execute("Plain text message")
    decrypted_message = context["decrypt_use_case"].execute(encrypted_message)

    assert decrypted_message == "Plain text message"
