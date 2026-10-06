import logging

from notification_context.application.commands import NotifyVaultStateChangedCommand
from notification_context.application.gateways import (
    NotificationPreferencesRepository,
    RecipientGateway,
)
from notification_context.domain.value_objects import Recipient, VaultStateChange
from shared_kernel.application.gateways import EmailGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError
from shared_kernel.domain.value_objects import OutgoingEmail

logger = logging.getLogger(__name__)


class NotifyVaultStateChangedUseCase(TracedUseCase):
    """Emails every user who opted in about a vault lock or unlock.

    Called once per state change: the vault context publishes exactly one event
    per lock or unlock, so this use case does not deduplicate anything itself.
    """

    def __init__(
        self,
        preferences_repository: NotificationPreferencesRepository,
        recipient_gateway: RecipientGateway,
        email_gateway: EmailGateway,
        app_base_url: str,
    ):
        self._preferences_repository = preferences_repository
        self._recipient_gateway = recipient_gateway
        self._email_gateway = email_gateway
        self._app_base_url = app_base_url

    def execute(self, command: NotifyVaultStateChangedCommand) -> None:
        user_ids = self._preferences_repository.list_user_ids_to_notify(command.change)
        if not user_ids:
            return
        recipients = self._recipient_gateway.get_recipients(user_ids)
        if not recipients:
            return

        subject, describe = self._message(command)
        emails = [
            OutgoingEmail(
                to=recipient.email,
                subject=subject,
                body=(
                    f"Hello {recipient.display_name},\n\n"
                    f"{describe}\n\n"
                    "You receive this email because you asked to be notified of vault "
                    f"locks and unlocks. You can change this in your profile: {self._app_base_url}/profile"
                ),
            )
            for recipient in recipients
        ]

        try:
            # One connection to the relay for every recipient rather than one per
            # recipient: a broadcast to hundreds of opted-in users must not open
            # hundreds of SMTP connections in series.
            failures = self._email_gateway.send_bulk(emails)
        except EmailDeliveryError as error:
            # The connection itself failed: nothing in the batch was sent.
            logger.error(
                "Failed to send vault %s email to any of %d recipient(s): %s",
                command.change.value,
                len(emails),
                error,
            )
            return

        for to, error in failures:
            # One undeliverable address must not keep the others from being told.
            logger.error("Failed to send vault %s email to %s: %s", command.change.value, to, error)

    def _message(self, command: NotifyVaultStateChangedCommand) -> tuple[str, str]:
        if command.change is VaultStateChange.UNLOCKED:
            return (
                "Le Coffre: the vault was unlocked",
                f"The vault was unlocked. Passwords are available again: {self._app_base_url}",
            )
        return (
            "Le Coffre: the vault was locked",
            f"The vault was locked {self._locked_by(command)}. Passwords are unavailable until the "
            f"share holders unlock it: {self._app_base_url}/unlock",
        )

    def _locked_by(self, command: NotifyVaultStateChangedCommand) -> str:
        if command.locked_by_user_id is None:
            return "because the server restarted"
        lockers: list[Recipient] = self._recipient_gateway.get_recipients([command.locked_by_user_id])
        return f"by {lockers[0].display_name}" if lockers else "by an administrator"
