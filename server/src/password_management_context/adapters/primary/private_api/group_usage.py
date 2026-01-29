from password_management_context.application.use_cases import IsGroupUsedUseCase
from password_management_context.application.commands import IsGroupUsedCommand
from uuid import UUID


class GroupUsageApi:
    def __init__(self, is_group_used_use_case: IsGroupUsedUseCase):
        self.is_group_used_use_case = is_group_used_use_case

    def is_group_used(self, group_id: UUID) -> bool:
        command = IsGroupUsedCommand(group_id=group_id)
        return self.is_group_used_use_case.execute(command)
