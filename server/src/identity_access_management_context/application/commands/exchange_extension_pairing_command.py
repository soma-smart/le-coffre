from dataclasses import dataclass


@dataclass
class ExchangeExtensionPairingCommand:
    """Anonymous, but the verifier proves the caller started this pairing."""

    user_code: str
    code_verifier: str
