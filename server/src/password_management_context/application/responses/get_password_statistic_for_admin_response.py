from dataclasses import dataclass


@dataclass
class GetPasswordStatisticForAdminResponse:
    password_count: int
