from dataclasses import dataclass


@dataclass
class SearchUsersCommand:
    query: str
