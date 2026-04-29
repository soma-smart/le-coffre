from dataclasses import dataclass


@dataclass
class GetStatisticForAdminResponse:
    user_count: int
    group_count: int
