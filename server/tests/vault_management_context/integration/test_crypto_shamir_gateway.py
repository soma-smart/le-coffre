import pytest

from vault_management_context.domain.value_objects import (
    VaultConfiguration,
)
from vault_management_context.adapters.secondary.gateways import CryptoShamirGateway


@pytest.fixture
def crypto_shamir():
    return CryptoShamirGateway()


def test_crypto_shamir_split_and_reconstruct(crypto_shamir: CryptoShamirGateway):
    nb_shares = 10
    threshold = 3
    vault_config = VaultConfiguration.create(nb_shares, threshold)
    share_result = crypto_shamir.create_shares(vault_config)

    assert len(share_result.shares) == nb_shares

    reconstructed = crypto_shamir.reconstruct_secret(share_result.shares[:threshold])
    assert reconstructed == share_result.master_key
