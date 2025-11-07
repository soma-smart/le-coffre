from dataclasses import dataclass


@dataclass(frozen=True)
class CanCreateAdminResponse:
    """Response indicating whether an admin can be created."""

    can_create: bool
