from uuid import UUID

from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    SetOwnerAccessUseCase,
    GetOwnerAccessUseCase,
)
from rights_access_context.domain.value_objects.permission import Permission
from shared_kernel.application.gateways import AccessController, AccessResult


class AccessControllerAdapter(AccessController):
    def __init__(
        self,
        check_use_case: CheckAccessUseCase,
        set_owner_use_case: SetOwnerAccessUseCase,
        get_owner_use_case: GetOwnerAccessUseCase,
    ):
        self.check_use_case = check_use_case
        self.set_owner_use_case = set_owner_use_case
        self.get_owner_use_case = get_owner_use_case

    def check_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        return self.check_use_case.execute(user_id, resource_id, Permission.READ)

    def check_update_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        return self.check_use_case.execute(user_id, resource_id, Permission.UPDATE)

    def check_delete_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        return self.check_use_case.execute(user_id, resource_id, Permission.DELETE)

    def set_owner(self, user_id: UUID, resource_id: UUID) -> None:
        self.set_owner_use_case.execute(user_id, resource_id)

    def is_owner(self, user_id: UUID, resource_id: UUID) -> bool:
        result = self.get_owner_use_case.execute(user_id, resource_id)
        return result is not None
