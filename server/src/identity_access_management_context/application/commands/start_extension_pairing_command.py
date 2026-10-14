from dataclasses import dataclass


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
