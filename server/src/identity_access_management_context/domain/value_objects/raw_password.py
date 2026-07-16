from dataclasses import dataclass, field

from identity_access_management_context.domain.exceptions import (
    CommonPasswordError,
    PasswordTooShortError,
)

MIN_PASSWORD_LENGTH = 12

# Well-known passwords that survive the length rule. Anything shorter than
# MIN_PASSWORD_LENGTH (password, 123456, admin, qwerty...) is already rejected by
# length, so listing it here would be dead weight. Matched as a whole string after
# normalisation, never as a substring: "SecurePassword123!" is a fine password and
# must not be rejected just because it contains "password".
COMMON_PASSWORDS = frozenset(
    {
        "password1234",
        "password12345",
        "password123456",
        "passwordpassword",
        "qwertyuiop12",
        "qwertyuiop123",
        "qwerty123456",
        "123456789012",
        "1234567890123",
        "12345678901234",
        "123456789012345",
        "1234567890123456",
        "administrator",
        "administrator1",
        "letmein12345",
        "letmein123456",
        "welcome12345",
        "welcome123456",
        "iloveyou1234",
        "iloveyou12345",
        "monkey123456",
        "abcd12345678",
        "trustno1234567",
        "passw0rd1234",
        "sunshine1234",
        "princess1234",
        "football1234",
        "baseball1234",
        "superman1234",
        "starwars1234",
        "dragon123456",
        "master123456",
        "shadow123456",
        "michael12345",
        "jennifer1234",
        "changeme1234",
        "secret123456",
        "default12345",
        "temporary123",
        "azertyuiop12",
        "motdepasse12",
        "motdepasse123",
    }
)


@dataclass(frozen=True)
class RawPassword:
    """A plaintext account password that satisfies the IAM password policy.

    Wraps the raw value only long enough to be hashed. Constructing one is the
    validation gate: an invalid account password cannot be represented.

    Domain Rules:
    - At least ``MIN_PASSWORD_LENGTH`` characters.
    - Must not be a well-known common password (whole-string match, normalised).

    No composition rules (uppercase/digit/special) by design, following NIST
    SP 800-63B: they push users toward predictable patterns ("Password1!") without
    meaningfully raising entropy, while hurting usability. Length plus a
    common-password blocklist is the stronger, better-supported combination.

    This policy covers *login credentials* only. Secrets stored inside the vault
    (password_management_context) are deliberately unconstrained: users must be able
    to store a legacy site's weak password.
    """

    # repr=False so the secret never leaks through the generated __repr__ in logs
    # or tracebacks.
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShortError(len(self.value), MIN_PASSWORD_LENGTH)

        if self.value.strip().casefold() in COMMON_PASSWORDS:
            raise CommonPasswordError()

    def __str__(self) -> str:
        return "RawPassword(***)"
