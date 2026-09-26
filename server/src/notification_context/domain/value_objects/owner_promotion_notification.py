from dataclasses import dataclass


@dataclass
class OwnerPromotionNotification:
    email: str
    display_name: str
    group_name: str
