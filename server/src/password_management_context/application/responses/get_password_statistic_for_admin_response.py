from dataclasses import dataclass


@dataclass
class GetPasswordStatisticForAdminResponse:
    password_count: int
    one_time_link_count: int
    active_one_time_link_count: int
