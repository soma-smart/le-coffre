from uuid import UUID

from sqlmodel import Session

from identity_access_management_context.application.gateways import ServiceAccountRepository, UserRepository
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.application.gateways import PrincipalRepository
from shared_kernel.domain.entities import Principal

from .model.principal_model import PrincipalKind, PrincipalTable


class SQLPrincipalRepository(SQLBaseRepository, PrincipalRepository):
    """Principals of any kind: the registry names the kind, whose own repository loads it."""

    def __init__(
        self, session: Session, user_repository: UserRepository, service_account_repository: ServiceAccountRepository
    ):
        super().__init__(session)
        self._user_repository = user_repository
        self._service_account_repository = service_account_repository

    def get_by_id(self, principal_id: UUID) -> Principal | None:
        registry = self._session.get(PrincipalTable, principal_id)
        if registry is None:
            return None
        match registry.kind:
            case PrincipalKind.USER:
                return self._user_repository.get_by_id(principal_id)
            case PrincipalKind.SERVICE_ACCOUNT:
                (account,) = self._service_account_repository.get_by_ids([principal_id])
                return account
