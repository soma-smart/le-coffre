import logging
from abc import abstractmethod
from dataclasses import dataclass
from functools import cached_property

from identity_access_management_context.application.commands.service_account import ServiceAccountCommand
from identity_access_management_context.application.gateways.service_account_event_repository import (
    ServiceAccountEventRepository,
)
from identity_access_management_context.application.gateways.service_account_repository import ServiceAccountRepository
from identity_access_management_context.application.responses.service_account_responses import ServiceAccountResponse
from identity_access_management_context.application.services.service_account_permission_service import (
    ServiceAccountPermissionService,
)
from identity_access_management_context.domain.events.service_account._event import ServiceAccountEvent
from shared_kernel.application.gateways.event_publisher_gateway import DomainEventPublisher
from shared_kernel.application.gateways.time_gateway import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


@dataclass(init=False)
class ServiceAccountUseCase[
    C: ServiceAccountCommand,
    E: ServiceAccountEvent,
    R: ServiceAccountResponse,
](TracedUseCase):
    """Service account use case."""

    _repository: ServiceAccountRepository
    _permissions: ServiceAccountPermissionService
    _event_publisher: DomainEventPublisher
    _event_repository: ServiceAccountEventRepository
    _time_provider: TimeGateway

    def __init__(
        self,
        service_account_repository: ServiceAccountRepository,
        permission_service: ServiceAccountPermissionService,
        event_publisher: DomainEventPublisher,
        service_account_event_repository: ServiceAccountEventRepository,
        time_provider: TimeGateway,
    ):
        self._repository = service_account_repository
        self._permissions = permission_service
        self._event_publisher = event_publisher
        self._event_repository = service_account_event_repository
        self._time_provider = time_provider

    @cached_property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @abstractmethod
    def _execute(self, command: C) -> tuple[E, R]: ...

    def execute(self, command: C) -> R:
        event, response = self._execute(command)
        self._event_repository.extend([event])
        self._event_publisher.publish(event)
        # TODO: Remove f-string in logger call
        self._logger.info(f"Published {event.__class__.__name__}", extra=event.event_data)
        return response
