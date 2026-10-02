from uuid import UUID

from identity_access_management_context.application.gateways import ServiceAccountRepository, UserRepository
from shared_kernel.application.gateways import PrincipalRepository
from shared_kernel.domain.entities import Principal


class FakePrincipalRepository(PrincipalRepository):
    """Looks the id up in each kind's repository, in place of the registry."""

    def __init__(self, user_repository: UserRepository, service_account_repository: ServiceAccountRepository):
        self._user_repository = user_repository
        self._service_account_repository = service_account_repository

    def get_by_id(self, principal_id: UUID) -> Principal | None:
        (account,) = self._service_account_repository.get_by_ids([principal_id])
        return self._user_repository.get_by_id(principal_id) or account
