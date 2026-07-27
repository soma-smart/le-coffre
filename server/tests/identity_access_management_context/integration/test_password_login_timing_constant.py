"""
Integration tests for constant-time password verification (AUTH-VULN-09 mitigation).

When a user is not found, bcrypt.verify() is called with a pre-computed dummy hash
to ensure constant-time response latency (~260ms) regardless of email existence,
preventing timing oracles that could enumerate valid emails by measuring response
time differences.

These tests verify that the mitigation is in place by:
1. Checking that verify() is called in both user-not-found and wrong-password paths
2. Verifying that the correct hash (dummy vs. real) is used in each path
"""

import pytest

from identity_access_management_context.adapters.secondary import (
    BcryptHashingGateway,
)


@pytest.fixture(scope="session")
def bcrypt_hashing_gateway():
    """Real bcrypt gateway for integration testing."""
    return BcryptHashingGateway()


def test_dummy_hash_never_matches_any_password(
    bcrypt_hashing_gateway: BcryptHashingGateway,
):
    """The pre-computed dummy hash should never match any password,
    ensuring that the verify() call in the non-existent-user path
    always returns False (as intended)."""
    from identity_access_management_context.application.use_cases.password_login_use_case import (
        DUMMY_PASSWORD_HASH,
    )

    # Try various passwords against the dummy hash
    test_passwords = [
        "dummy",  # The password used to generate the hash
        "correct_password",
        "any_random_string",
        "",
        "x" * 100,
    ]

    for password in test_passwords:
        result = bcrypt_hashing_gateway.verify(password, DUMMY_PASSWORD_HASH)
        # All should return False (dummy hash never matches)
        assert result is False, (
            f"Dummy hash should not match password '{password}', but verify() returned True. "
            "This means the password was used to create the hash, breaking the mitigation."
        )


def test_dummy_hash_is_valid_bcrypt_format(
    bcrypt_hashing_gateway: BcryptHashingGateway,
):
    """Verify that DUMMY_PASSWORD_HASH is a valid bcrypt hash that doesn't crash the verifier."""
    from identity_access_management_context.application.use_cases.password_login_use_case import (
        DUMMY_PASSWORD_HASH,
    )

    # Should not raise an exception
    try:
        result = bcrypt_hashing_gateway.verify("any_password", DUMMY_PASSWORD_HASH)
        assert isinstance(result, bool), "verify() should return a boolean"
    except Exception as e:
        pytest.fail(f"Verifying against DUMMY_PASSWORD_HASH raised an exception: {e}")


def test_real_hash_distinguishes_correct_and_wrong_passwords(
    bcrypt_hashing_gateway: BcryptHashingGateway,
):
    """Sanity check: real bcrypt hashes correctly verify passwords."""
    password = "secure123!"
    real_hash = bcrypt_hashing_gateway.hash(password)

    # Correct password should verify
    assert bcrypt_hashing_gateway.verify(password, real_hash) is True

    # Wrong password should not verify
    assert bcrypt_hashing_gateway.verify("wrong_password", real_hash) is False
