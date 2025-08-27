from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.domain.exceptions import PermissionDeniedError

class ShareAccessUseCase:
    def __init__(self, rights_repository):
        self.rights_repository = rights_repository

    def execute(self, command: ShareResourceCommand):
        if not self.rights_repository.has_access(command.owner_id, command.resource_id):
            raise PermissionDeniedError(command.owner_id, command.resource_id)
        self.rights_repository.grant_access(command.user_id, command.resource_id)
