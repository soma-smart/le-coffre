from dataclasses import dataclass, field

from identity_access_management_context.domain.exceptions import (
    CommonPasswordError,
    PasswordTooShortError,
)

# SP 800-63B-4 §3.1.1.2: "Verifiers and CSPs SHALL require passwords that are used as
# a single-factor authentication mechanism to be a minimum of 15 characters in
# length." Login here is single-factor, so 15 is the floor, not the 8 allowed for a
# password used as one factor of an MFA flow.
MIN_PASSWORD_LENGTH = 15

# Passwords that survive the length rule. Anything shorter than MIN_PASSWORD_LENGTH
# (password, 123456, motdepasse12...) is already rejected by length, so listing it
# here would be dead weight.
#
# Honest scope: this list is reasoned, not measured. Public frequency rankings from
# breach corpora exist for short passwords, but the population of real-world 15+
# character passwords is too sparse to rank reliably, so these are extrapolated
# patterns (runs, repeats, keyboard walks, lengthened classics) rather than a copied
# top-N. The French entries are a judgement call for our userbase, not data. Length
# does the real work; this list is a thin net over the residue, and it satisfies the
# SHALL below. A blocklist that genuinely earns its keep means checking against Have
# I Been Pwned (k-anonymity), which is a separate, bigger decision for a self-hosted
# product that may run air-gapped.
#
# SP 800-63B-4 §3.1.1.2: "verifiers SHALL compare the prospective secret against a
# blocklist that contains known commonly used, expected, or compromised passwords.
# The entire password SHALL be subject to comparison, not substrings or words that
# might be contained therein." Hence whole-string matching after normalisation:
# "SecurePassword123!" is a fine password and must not be rejected for containing
# "password".
COMMON_PASSWORDS = frozenset(
    {
        # Runs and repeated characters
        "123456789012345",
        "1234567890123456",
        "111111111111111",
        "000000000000000",
        "aaaaaaaaaaaaaaa",
        # Words repeated to reach the length
        "passwordpassword",
        "motdepassemotdepasse",
        "trustno1trustno1",
        # Keyboard walks
        "qwertyuiopasdfgh",
        "qwertyuiopasdfghjkl",
        "azertyuiopqsdfgh",
        "qwertyuiop123456",
        # Classics padded out to clear the length rule
        "password12345678",
        "administrator123",
        "motdepasse12345",
        "letmein123456789",
        "welcome123456789",
        "iloveyou12345678",
        "changeme12345678",
        "thisismypassword",
        # Famous passphrase, in wordlists since xkcd 936
        "correcthorsebatterystaple",
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

    No composition rules (uppercase/digit/special) by design. This is not a
    preference: NIST SP 800-63B-4 §3.1.1.2 states "Verifiers and CSPs SHALL NOT
    impose other composition rules (e.g., requiring mixtures of different character
    types) for passwords." Such rules push users toward predictable patterns
    ("Password1!") without meaningfully raising entropy, while hurting usability.
    Length carries the policy; see COMMON_PASSWORDS for what the blocklist is and
    is not worth.

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
