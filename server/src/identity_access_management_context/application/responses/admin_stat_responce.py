from dataclasses import dataclass


@dataclass
class AdminStatResponse:
    groupCount: int
    userCount: int
    passwordCount: int
