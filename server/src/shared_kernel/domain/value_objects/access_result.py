from dataclasses import dataclass
from enum import Enum


class Granted(Enum):
    NOT_FOUND = "NotFound"
    ACCESS = "Access"


@dataclass(frozen=True)
class AccessResult:
    granted: Granted
    is_owner: bool = False
