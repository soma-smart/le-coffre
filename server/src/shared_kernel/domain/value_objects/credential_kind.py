from enum import Enum


class CredentialKind(Enum):
    """How a caller proved who they are.

    The distinction matters because the two carry different authority. A session
    cookie is the user acting directly, with everything they are allowed to do.
    An extension credential is a long-lived, read-only grant sitting in a browser
    profile, and is deliberately narrower.
    """

    SESSION = "session"
    EXTENSION = "extension"
