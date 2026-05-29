from enum import Enum


class AccessRole(Enum):
    """How a subject relates to the thing granting it access.

    Used on two axes:
    - a user relative to a group (owner or member of the group)
    - a group relative to a password (owner of the password, or merely shared with it)
    """

    OWNER = "owner"
    MEMBER = "member"
