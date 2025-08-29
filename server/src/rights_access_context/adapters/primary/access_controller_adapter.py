from uuid import UUID

from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
    GrantAccessUseCase,
)
from shared_kernel.access_control import AccessController


class AccessControllerAdapter(AccessController):
    def __init__(
        self, check_use_case: CheckAccessUseCase, grant_use_case: GrantAccessUseCase
    ):
        self.check_use_case = check_use_case
        self.grant_use_case = grant_use_case

    def check_access(self, user_id: UUID, resource_id: UUID) -> bool:
        access_result = self.check_use_case.execute(user_id, resource_id)
        return access_result.granted

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.grant_use_case.execute(user_id, resource_id)
