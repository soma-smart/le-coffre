from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PresentedCredential:
    """The stored credential a request authenticated with.

    Kept apart from `AuthenticatedPrincipal` on purpose: who is calling and how
    they proved it are two questions. A request authenticated by its session has
    none, a session is not a credential record.
    """

    credential_id: UUID

    read_only: bool
    """Temporary, stands in for a permission and grant system: see TokenCredentialRecord.read_only."""
