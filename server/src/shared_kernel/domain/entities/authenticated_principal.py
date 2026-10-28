from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Whoever is behind a request on a route open to both humans and machines.

    Only carries what such a route may rely on: an identity. Roles are left out on
    purpose, a route needing them is a human-only route.
    """

    principal_id: UUID
    kind: Literal["user", "service_account"]
