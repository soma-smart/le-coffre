import pytest

from identity_access_management_context.adapters.secondary import BcryptHashingGateway


@pytest.fixture
def bcrypt_hashing_gateways():
    return BcryptHashingGateway()


def test_bcrypt_hashing_gateway_compare(bcrypt_hashing_gateways: BcryptHashingGateway):
    password = "securepassword123"
    hashed = bcrypt_hashing_gateways.hash(password)
    assert bcrypt_hashing_gateways.verify(password, hashed)


def test_bcrypt_hashing_gateway_compare_fail(
    bcrypt_hashing_gateways: BcryptHashingGateway,
):
    password = "securepassword123"
    wrong_password = "wrongpassword456"
    hashed = bcrypt_hashing_gateways.hash(password)
    assert not bcrypt_hashing_gateways.verify(wrong_password, hashed)


def test_bcrypt_hashing_gateway_hash(bcrypt_hashing_gateways: BcryptHashingGateway):
    password = "securepassword123"
    hashed = bcrypt_hashing_gateways.hash(password)
    assert hashed != password


def test_bcrypt_hashing_gateway_hash_different(
    bcrypt_hashing_gateways: BcryptHashingGateway,
):
    password = "securepassword123"
    hashed1 = bcrypt_hashing_gateways.hash(password)
    hashed2 = bcrypt_hashing_gateways.hash(password)
    assert hashed1 != hashed2
