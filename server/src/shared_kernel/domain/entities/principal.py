from dataclasses import dataclass
from uuid import UUID

# Enforcing field `id`, that requires hashability, to be `UUID` on the whole system.


@dataclass(kw_only=True)
class Principal:
    """An actor that performs operations on resources.

    Only the identity lives here. How a principal proved who it is belongs to
    `Credential`, and what it may do is still decided per resource.
    """

    id: UUID
