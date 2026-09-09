import secrets
from dataclasses import dataclass

from identity_access_management_context.domain.exceptions import (
    InvalidPairingUserCodeError,
)

# Crockford-style alphabet: no I, L, O, U. The whole point of this code is that
# a human reads it off the extension popup and matches it against the approval
# page, so pairs that look alike in a proportional font are removed rather than
# left to the user to disambiguate.
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

GROUP_LENGTH = 4
GROUP_COUNT = 2
CODE_LENGTH = GROUP_LENGTH * GROUP_COUNT + (GROUP_COUNT - 1)  # includes the dash


@dataclass(frozen=True)
class PairingUserCode:
    """The short code shown in BOTH the extension and the approval page.

    This is the only anti-phishing control available in the pairing flow: it is
    what lets the user tell "my extension asked for this" from "some page asked
    for this". It is not a secret, it appears on screen and in a URL fragment,
    and it grants nothing on its own; redeeming a pairing additionally requires
    the PKCE verifier, which never leaves the extension.

    8 characters over a 32-symbol alphabet is 40 bits. Guessing one inside its
    5-minute window would also have to beat the per-IP rate-limit bucket on the
    pairing routes, and would still yield only a pending pairing the attacker
    cannot redeem.
    """

    value: str

    def __post_init__(self) -> None:
        if not self._is_well_formed(self.value):
            raise InvalidPairingUserCodeError()

    @staticmethod
    def _is_well_formed(value: str) -> bool:
        groups = value.split("-")
        if len(groups) != GROUP_COUNT:
            return False
        return all(len(group) == GROUP_LENGTH and all(character in ALPHABET for character in group) for group in groups)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> "PairingUserCode":
        groups = ["".join(secrets.choice(ALPHABET) for _ in range(GROUP_LENGTH)) for _ in range(GROUP_COUNT)]
        return cls(value="-".join(groups))

    @classmethod
    def parse(cls, value: str) -> "PairingUserCode":
        """Normalise user-visible input before validating.

        The code is meant to be typed or pasted by a human, so case and
        surrounding whitespace are not signal.
        """
        return cls(value=value.strip().upper())
