from uuid import UUID

from rights_access_context.application.use_cases import CheckAccessUseCase
from shared_kernel.access_control import AccessChecker


class AccessCheckerAdapter(AccessChecker):
    def __init__(self, use_case: CheckAccessUseCase):
        self.use_case = use_case

    def check_access(self, user_id: UUID, resource_id: UUID) -> bool:
        access_result = self.use_case.execute(user_id, resource_id)

        return access_result.granted
