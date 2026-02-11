from enum import Enum


class VaultStatus(Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    NOT_SETUP = "NOT_SETUP"
    PENDING = "PENDING"
    SETUPED = "SETUPED"
    PENDING_UNLOCK = "PENDING_UNLOCK"
