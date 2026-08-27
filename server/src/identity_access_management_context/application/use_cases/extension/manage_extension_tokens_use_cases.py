import logging
from uuid import UUID

from identity_access_management_context.application.commands import (
    ListExtensionTokensCommand,
    RevokeAllExtensionTokensCommand,
    RevokeExtensionTokenCommand,
)
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.responses import (
    ExtensionTokenSummary,
    ListExtensionTokensResponse,
)
from identity_access_management_context.domain.events import ExtensionTokenRevokedEvent
from identity_access_management_context.domain.exceptions import ExtensionTokenNotFoundError
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)

REVOCATION_REASON_USER_REQUEST = "user_request"
REVOCATION_REASON_USER_DELETED = "user_deleted"


def record_extension_revocation(
    event_publisher: DomainEventPublisher,
    admin_event_repository: AdminEventRepository,
    user_id: UUID,
    token_id: UUID | None,
    reason: str,
    revoked_count: int,
) -> None:
    """Publish and persist the audit trail for a revocation.

    Shared by the single and bulk revocations so both land in the audit log in
    the same shape. `reason` is what separates "the user tidied up" from
    "access was cut for them" when the trail is read back later.
    """
    event = ExtensionTokenRevokedEvent(
        user_id=user_id,
        token_id=token_id,
        reason=reason,
        revoked_count=revoked_count,
    )
    event_publisher.publish(event)
    admin_event_repository.append_event(
        event_id=event.event_id,
        event_type=type(event).__name__,
        occurred_on=event.occurred_on,
        actor_user_id=user_id,
        event_data={
            "token_id": str(token_id) if token_id else None,
            "reason": reason,
            "revoked_count": revoked_count,
        },
    )
    logger.info(
        "Extension token(s) revoked",
        extra={"user_id": str(user_id), "reason": reason, "revoked_count": revoked_count},
    )


class ListExtensionTokensUseCase(TracedUseCase):
    """The connected-devices screen.

    Returns revoked and expired entries too: a user checking "did I actually
    disconnect that laptop" needs to see the answer, not an empty row.
    """

    def __init__(
        self,
        extension_token_repository: ExtensionTokenRepository,
        time_provider: TimeGateway,
    ):
        self._extension_token_repository = extension_token_repository
        self._time_provider = time_provider

    def execute(self, command: ListExtensionTokensCommand) -> ListExtensionTokensResponse:
        now = self._time_provider.get_current_time()
        tokens = self._extension_token_repository.list_for_user(command.requesting_user.user_id)

        return ListExtensionTokensResponse(
            tokens=[
                ExtensionTokenSummary(
                    id=token.id,
                    device_name=token.device_name,
                    created_at=token.created_at,
                    expires_at=token.expires_at,
                    last_used_at=token.last_used_at,
                    revoked_at=token.revoked_at,
                    created_from_ip=token.created_from_ip,
                    is_active=token.is_active(now),
                )
                for token in tokens
            ]
        )


class RevokeExtensionTokenUseCase(TracedUseCase):
    """Disconnect one device."""

    def __init__(
        self,
        extension_token_repository: ExtensionTokenRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
    ):
        self._extension_token_repository = extension_token_repository
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository
        self._time_provider = time_provider

    def execute(self, command: RevokeExtensionTokenCommand) -> None:
        token = self._extension_token_repository.get_by_id(command.token_id)

        # Someone else's token is reported as missing rather than forbidden, so
        # this route cannot be used to discover which token ids exist.
        if token is None or token.user_id != command.requesting_user.user_id:
            raise ExtensionTokenNotFoundError()

        now = self._time_provider.get_current_time()
        if not self._extension_token_repository.revoke(token.id, now):
            # Already revoked. Idempotent from the caller's point of view: the
            # device is disconnected either way, and re-recording would put a
            # second, misleading entry in the audit trail.
            return

        record_extension_revocation(
            self._event_publisher,
            self._admin_event_repository,
            user_id=command.requesting_user.user_id,
            token_id=token.id,
            reason=REVOCATION_REASON_USER_REQUEST,
            revoked_count=1,
        )


class RevokeAllExtensionTokensUseCase(TracedUseCase):
    """Disconnect every device at once."""

    def __init__(
        self,
        extension_token_repository: ExtensionTokenRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
    ):
        self._extension_token_repository = extension_token_repository
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository
        self._time_provider = time_provider

    def execute(self, command: RevokeAllExtensionTokensCommand) -> int:
        user_id = command.requesting_user.user_id
        now = self._time_provider.get_current_time()
        revoked = self._extension_token_repository.revoke_all_for_user(user_id, now)

        if revoked:
            record_extension_revocation(
                self._event_publisher,
                self._admin_event_repository,
                user_id=user_id,
                token_id=None,
                reason=REVOCATION_REASON_USER_REQUEST,
                revoked_count=revoked,
            )
        return revoked
