from dataclasses import dataclass


@dataclass
class ListGroupsCommand:
    include_personal: bool = True
