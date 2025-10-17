from group_management_context.application.commands import CreateGroupCommand
from group_management_context.application.gateways import GroupRepository
from group_management_context.application.responses import CreateGroupResponse
from group_management_context.domain.exceptions import (
    GroupNameAlreadyExistsException,
    GroupNameTooShortException,
)
from group_management_context.domain.group import Group


MIN_GROUP_NAME_LENGTH = 10

class CreateGroupUseCase:
    def __init__(self, group_repository: GroupRepository):
        self._group_repository = group_repository

    def execute(self, command: CreateGroupCommand) -> CreateGroupResponse:
        if len(command.name) < MIN_GROUP_NAME_LENGTH:
            raise GroupNameTooShortException(MIN_GROUP_NAME_LENGTH)
        
        if self._group_repository.exists_by_name(command.name):
            raise GroupNameAlreadyExistsException(command.name)
        
        group = Group(id=command.group_id, name=command.name, owner_id=command.user_id)
        self._group_repository.save(group)
        return CreateGroupResponse(group_id=command.group_id)
