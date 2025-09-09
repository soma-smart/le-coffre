from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.domain.exceptions import PermissionDeniedError

class ShareAccessUseCase:
    def __init__(self, rights_repository):
        self.rights_repository = rights_repository

    def execute(self, command: ShareResourceCommand):
        if not self.rights_repository.has_permission(command.owner_id, command.resource_id):
            raise PermissionDeniedError(command.owner_id, command.resource_id)
        self.rights_repository.add_permission(command.user_id, command.resource_id)
