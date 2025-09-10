import re

from password_management_context.domain.exceptions import (
    PasswordComplexityError,
    PasswordTooShortError,
    PasswordMissingUppercaseError,
    PasswordMissingLowercaseError,
    PasswordMissingDigitError,
    PasswordMissingSpecialCharError,
    PasswordContainsForbiddenPatternError,
    PasswordMultipleComplexityError,
)


class PasswordComplexityService:
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True
    FORBIDDEN_PATTERNS = ["123456", "password", "qwerty"]

    @staticmethod
    def validate(password: str) -> None:
        """
        Validate password complexity and raise specific exceptions for violations.

        Raises:
            PasswordComplexityError: For single violations
            PasswordMultipleComplexityError: For multiple violations
        """
        violations = []

        if len(password) < PasswordComplexityService.MIN_LENGTH:
            violations.append(
                PasswordTooShortError(
                    len(password), PasswordComplexityService.MIN_LENGTH
                )
            )

        if PasswordComplexityService.REQUIRE_UPPERCASE and not re.search(
            r"[A-Z]", password
        ):
            violations.append(PasswordMissingUppercaseError())

        if PasswordComplexityService.REQUIRE_LOWERCASE and not re.search(
            r"[a-z]", password
        ):
            violations.append(PasswordMissingLowercaseError())

        if PasswordComplexityService.REQUIRE_DIGITS and not re.search(r"\d", password):
            violations.append(PasswordMissingDigitError())

        if PasswordComplexityService.REQUIRE_SPECIAL_CHARS and not re.search(
            r"[!@#$%^&*(),.?\":{}|<>]", password
        ):
            violations.append(PasswordMissingSpecialCharError())

        for pattern in PasswordComplexityService.FORBIDDEN_PATTERNS:
            if pattern.lower() in password.lower():
                violations.append(PasswordContainsForbiddenPatternError(pattern))

        if violations:
            if len(violations) == 1:
                raise violations[0]
            else:
                raise PasswordMultipleComplexityError(violations)

    @staticmethod
    def is_valid(password: str) -> bool:
        """Check if password is valid without raising exceptions"""
        try:
            PasswordComplexityService.validate(password)
            return True
        except PasswordComplexityError:
            return False
