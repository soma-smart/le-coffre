from dataclasses import dataclass


@dataclass(frozen=True)
class IsSsoConfigSetResponse:
    is_set: bool
