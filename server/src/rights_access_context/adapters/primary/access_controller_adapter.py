from uuid import UUID

from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    GrantAccessUseCase,
)
from rights_access_context.domain.value_objects.permission import Permission
from shared_kernel.access_control import AccessController, AccessResult


class AccessControllerAdapter(AccessController):
    def __init__(
        self, check_use_case: CheckAccessUseCase, grant_use_case: GrantAccessUseCase
    ):
        self.check_use_case = check_use_case
        self.grant_use_case = grant_use_case

    def check_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        return self.check_use_case.execute(user_id, resource_id, Permission.READ)

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.grant_use_case.execute(user_id, resource_id, Permission.READ)

    def check_update_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        return self.check_use_case.execute(user_id, resource_id, Permission.UPDATE)

    def grant_update_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.grant_use_case.execute(user_id, resource_id, Permission.UPDATE)

    def check_delete_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        return self.check_use_case.execute(user_id, resource_id, Permission.DELETE)

    def grant_delete_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.grant_use_case.execute(user_id, resource_id, Permission.DELETE)
