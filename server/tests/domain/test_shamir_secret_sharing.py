import pytest

from src.domain.crypto.shamir_service import ShamirSecretService


def test_given_secret_and_params_when_split_then_returns_n_shares():
    num_shares = 5
    threshold = 3

    shares = ShamirSecretService().split_secret(threshold, num_shares)
    assert isinstance(shares, list)
    assert len(shares) == num_shares
