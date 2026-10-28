from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from identity_access_management_context.domain.entities import ServiceAccount, User
from shared_kernel.domain.entities import Principal

PrincipalKind = Literal["user", "service_account"]


@dataclass(frozen=True)
class GetPrincipalResponse:
    """Who a principal is, as shown to humans: enough to name an actor, nothing more."""

    principal_id: UUID
    kind: PrincipalKind
    display_name: str

    @classmethod
    def of(cls, principal: Principal) -> "GetPrincipalResponse":
        return cls(principal_id=principal.id, kind=cls._kind_of(principal), display_name=principal.display_name)

    @staticmethod
    def _kind_of(principal: Principal) -> PrincipalKind:
        match principal:
            case User():
                return "user"
            case ServiceAccount():
                return "service_account"
        raise TypeError(f"Unknown kind of principal: {type(principal).__name__}")
