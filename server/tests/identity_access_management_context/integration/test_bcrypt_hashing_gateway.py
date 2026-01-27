import pytest

from identity_access_management_context.adapters.secondary import BcryptHashingGateway


@pytest.fixture(scope="session")
def bcrypt_hashing_gateways():
    return BcryptHashingGateway()


def test_should_verify_password_when_correct_password_provided(
    bcrypt_hashing_gateways: BcryptHashingGateway,
):
    password = "securepassword123"
    hashed = bcrypt_hashing_gateways.hash(password)
    assert bcrypt_hashing_gateways.verify(password, hashed)


def test_should_fail_verification_when_wrong_password_provided(
    bcrypt_hashing_gateways: BcryptHashingGateway,
):
    password = "securepassword123"
    wrong_password = "wrongpassword456"
    hashed = bcrypt_hashing_gateways.hash(password)
    assert not bcrypt_hashing_gateways.verify(wrong_password, hashed)


def test_should_hash_password_successfully(
    bcrypt_hashing_gateways: BcryptHashingGateway,
):
    password = "securepassword123"
    hashed = bcrypt_hashing_gateways.hash(password)
    assert hashed != password


def test_should_generate_different_hashes_when_hashing_same_password(
    bcrypt_hashing_gateways: BcryptHashingGateway,
):
    password = "securepassword123"
    hashed1 = bcrypt_hashing_gateways.hash(password)
    hashed2 = bcrypt_hashing_gateways.hash(password)
    assert hashed1 != hashed2
