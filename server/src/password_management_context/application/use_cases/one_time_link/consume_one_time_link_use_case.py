import logging

from password_management_context.application.commands import ConsumeOneTimeLinkCommand
from password_management_context.application.gateways import (
    OneTimeLinkRepository,
    PasswordEncryptionGateway,
    PasswordEventRepository,
    PasswordRepository,
    PasswordVaultAccessGateway,
)
from password_management_context.application.responses import ConsumedOneTimeLinkResponse
from password_management_context.application.services import PasswordEventStorageService
from password_management_context.domain.events import OneTimeLinkReadEvent
from password_management_context.domain.exceptions import (
    OneTimeLinkAlreadyUsedError,
    OneTimeLinkNotFoundError,
    PasswordNotFoundError,
)
from password_management_context.domain.value_objects import OneTimeLinkToken
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class ConsumeOneTimeLinkUseCase(TracedUseCase):
    """Redeem a one-time link and hand back the secret. No authentication."""

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        password_repository: PasswordRepository,
        password_encryption_gateway: PasswordEncryptionGateway,
        password_vault_access_gateway: PasswordVaultAccessGateway,
        password_event_repository: PasswordEventRepository,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.password_repository = password_repository
        self.password_encryption_gateway = password_encryption_gateway
        self.password_vault_access_gateway = password_vault_access_gateway
        self.password_event_repository = password_event_repository
        self.time_gateway = time_gateway

    def execute(self, command: ConsumeOneTimeLinkCommand) -> ConsumedOneTimeLinkResponse:
        token = OneTimeLinkToken(value=command.token)

        link = self.one_time_link_repository.get_by_token_hash(token.hashed())
        if link is None:
            raise OneTimeLinkNotFoundError()

        now = self.time_gateway.get_current_time()
        link.ensure_consumable(now)

        try:
            password_entity = self.password_repository.get_by_id(link.password_id)
        except PasswordNotFoundError as e:
            # The password was deleted after the link was issued. Reported as an
            # unusable link rather than a missing password, so the anonymous
            # caller learns nothing about what exists on the other side.
            raise OneTimeLinkNotFoundError() from e

        # Checked before consuming, not after: a locked vault is an operational
        # incident, and burning the recipient's only link over it would be
        # wrong. The caller gets a 503 and the link stays usable.
        # A vault locked between this check and the decrypt below would still
        # consume the link, but that window is a couple of statements wide.
        self.password_vault_access_gateway.ensure_vault_is_unlocked()

        # Single conditional write. Two concurrent redemptions both reach here,
        # only one gets True, so the secret is released exactly once.
        if not self.one_time_link_repository.consume(link.id, now):
            raise OneTimeLinkAlreadyUsedError()

        decrypted_password = self.password_encryption_gateway.decrypt(password_entity.encrypted_value)

        logger.info(
            "One-time link consumed",
            extra={"password_id": str(link.password_id), "link_id": str(link.id)},
        )

        event = OneTimeLinkReadEvent(
            password_id=link.password_id,
            link_id=link.id,
            created_by_user_id=link.created_by_user_id,
        )
        PasswordEventStorageService(self.password_event_repository).store_event(event)

        return ConsumedOneTimeLinkResponse(
            name=password_entity.name,
            password=decrypted_password,
            login=password_entity.login,
            url=password_entity.url,
        )
