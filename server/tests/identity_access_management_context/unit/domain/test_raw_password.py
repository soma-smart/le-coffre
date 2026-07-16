import pytest

from identity_access_management_context.domain.exceptions import (
    CommonPasswordError,
    IdentityAccessManagementDomainError,
    PasswordPolicyViolationError,
    PasswordTooShortError,
)
from identity_access_management_context.domain.value_objects import (
    MIN_PASSWORD_LENGTH,
    RawPassword,
)


class TestLengthRule:
    @pytest.mark.parametrize("value", ["a", "short", "elevenchars"])
    def test_should_reject_password_below_minimum_length(self, value):
        with pytest.raises(PasswordTooShortError) as exc_info:
            RawPassword(value)

        assert exc_info.value.current_length == len(value)
        assert exc_info.value.min_length == MIN_PASSWORD_LENGTH

    def test_should_accept_password_at_exactly_the_minimum_length(self):
        value = "a" * MIN_PASSWORD_LENGTH

        assert RawPassword(value).value == value


class TestCommonPasswordRule:
    @pytest.mark.parametrize("value", ["password1234", "administrator", "qwertyuiop12"])
    def test_should_reject_a_well_known_common_password(self, value):
        with pytest.raises(CommonPasswordError):
            RawPassword(value)

    @pytest.mark.parametrize("value", ["PassWord1234", "  password1234  ", "PASSWORD1234"])
    def test_should_reject_common_password_regardless_of_case_or_padding(self, value):
        with pytest.raises(CommonPasswordError):
            RawPassword(value)

    @pytest.mark.parametrize(
        "value",
        [
            "SecurePassword123!",  # contains "password" but is not one
            "my_plain_password",
            "correct horse battery staple",
        ],
    )
    def test_should_accept_a_password_merely_containing_a_common_word(self, value):
        # Whole-string match, never substring: rejecting these would be a false positive.
        assert RawPassword(value).value == value


class TestSecrecyAndTyping:
    def test_should_not_expose_the_secret_in_repr_or_str(self):
        password = RawPassword("SecurePassword123!")

        assert "SecurePassword123!" not in repr(password)
        assert "SecurePassword123!" not in str(password)

    def test_violations_should_be_catchable_as_the_policy_family_and_domain_error(self):
        # Routes rely on the IdentityAccessManagementDomainError arm to answer 400.
        with pytest.raises(PasswordPolicyViolationError):
            RawPassword("a")
        with pytest.raises(IdentityAccessManagementDomainError):
            RawPassword("a")
