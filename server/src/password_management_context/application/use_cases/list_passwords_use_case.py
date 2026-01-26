from typing import List, Optional
from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
)
from password_management_context.application.responses import PasswordMetadataResponse
from password_management_context.domain.exceptions import FolderNotFoundError
from password_management_context.domain.services import PasswordAccessService
from password_management_context.domain.events import (
    PasswordsListedEvent,
)
from shared_kernel.pubsub.gateway.event_publisher_gateway import DomainEventPublisher


class ListPasswordsUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_access_service: PasswordAccessService,
        event_publisher: DomainEventPublisher,
    ):
        self.password_repository = password_repository
        self.password_access_service = password_access_service
        self.event_publisher = event_publisher

    def execute(
        self, requester_id: UUID, folder: Optional[str] = None
    ) -> List[PasswordMetadataResponse]:
        password_entities = self.password_repository.list_all(folder)

        if folder and len(password_entities) == 0:
            raise FolderNotFoundError(folder)

        password_responses = []
        for password_entity in password_entities:
            access_info = self.password_access_service.user_has_access_through_groups(
                requester_id, password_entity.id
            )
            if access_info is not None:
                user_group_id, owner_group_id = access_info
                password_response = PasswordMetadataResponse(
                    id=password_entity.id,
                    name=password_entity.name,
                    folder=password_entity.folder,
                    group_id=owner_group_id,
                )
                password_responses.append(password_response)

        # Publish domain event
        event = PasswordsListedEvent(
            listed_by_user_id=requester_id,
            folder=folder,
            count=len(password_responses),
        )
        self.event_publisher.publish(event)

        return password_responses
