from dataclasses import dataclass
from uuid import UUID

from shared_kernel.domain.entities import ValidatedUser


@dataclass
class StartExtensionPairingCommand:
    """Anonymous. The extension registers its challenge before opening the tab.

    Registering first is what makes the user_code a server-vouched fact rather
    than attacker-supplied text, which is what lets the approval page display it
    for the user to match against their extension.
    """

    code_challenge: str
    code_challenge_method: str
    device_name: str
    created_from_ip: str | None = None


@dataclass
class GetExtensionPairingCommand:
    """Cookie-authenticated. Backs the approval page."""

    user_code: str
    requesting_user: ValidatedUser


@dataclass
class ApproveExtensionPairingCommand:
    user_code: str
    requesting_user: ValidatedUser


@dataclass
class DenyExtensionPairingCommand:
    user_code: str
    requesting_user: ValidatedUser


@dataclass
class ExchangeExtensionPairingCommand:
    """Anonymous, but the verifier proves the caller started this pairing."""

    user_code: str
    code_verifier: str


@dataclass
class ValidateExtensionTokenCommand:
    raw_token: str


@dataclass
class ListExtensionTokensCommand:
    requesting_user: ValidatedUser


@dataclass
class RevokeExtensionTokenCommand:
    token_id: UUID
    requesting_user: ValidatedUser


@dataclass
class RevokeAllExtensionTokensCommand:
    requesting_user: ValidatedUser
