import logging

from notification_context.application.commands import NotifyExtensionPairedCommand
from notification_context.application.gateways import UserContactGateway
from shared_kernel.application.gateways import EmailGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


class NotifyExtensionPairedUseCase(TracedUseCase):
    """Tell the account owner that a browser extension was just connected.

    The approval page is where a phishing attempt is meant to be caught, but
    a page can be misread. This is the net under it: every pairing that
    mints a credential produces an email the owner did not have to ask for,
    naming the device and the address it came from, with the way to cut it.
    Someone who approved a pairing they did not start learns about it within
    minutes rather than at the end of the token's life.

    Courtesy send, like the owner-promotion email: the credential is already
    issued, so a lookup or delivery failure is logged and never surfaces.
    """

    def __init__(self, user_contact_gateway: UserContactGateway, email_gateway: EmailGateway, app_base_url: str):
        self._user_contact_gateway = user_contact_gateway
        self._email_gateway = email_gateway
        self._app_base_url = app_base_url

    def execute(self, command: NotifyExtensionPairedCommand) -> None:
        try:
            contact = self._user_contact_gateway.get_contact(command.user_id)
        except Exception:  # noqa: BLE001 - courtesy send: a lookup failure must not surface on the already-completed pairing
            logger.error("Failed to look up the contact for user=%s", command.user_id, exc_info=True)
            return

        if contact is None:
            logger.warning("No contact found for user=%s; skipping the extension-paired email", command.user_id)
            return

        origin = f" from {command.created_from_ip}" if command.created_from_ip else ""
        subject = "A browser extension was connected to your account"
        body = (
            f"Hello {contact.display_name},\n\n"
            f"A browser extension was connected to your Le Coffre account on "
            f"{command.paired_at:%Y-%m-%d at %H:%M}{origin}.\n"
            f'Device, as reported by the extension: "{command.device_name}"\n\n'
            "It can read the passwords you can already read, nothing more, until it is "
            "disconnected or expires.\n\n"
            "If this was not you, disconnect it now from your profile and change your password:\n"
            f"{self._app_base_url}/profile"
        )

        try:
            self._email_gateway.send(to=contact.email, subject=subject, body=body)
        except EmailDeliveryError:
            logger.error("Failed to send the extension-paired email to %s", contact.email, exc_info=True)
