from enum import Enum
from dataclasses import dataclass


class Granted(Enum):
    NOT_FOUND = "NotFound"
    VIEW_ONLY = "ViewOnly"
    ACCESS = "Access"


@dataclass(frozen=True)
class AccessResult:
    granted: Granted
    is_owner: bool = False
