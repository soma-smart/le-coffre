from datetime import datetime, timezone

from notification_context.domain.value_objects import Recipient
from shared_kernel.domain.value_objects import OutgoingEmail

# What the creator of a one-time link is told, and nothing more. These emails never
# carry the link's token nor the secret: they only point at the list of the user's
# links, where the link can be looked at.


def _readable_utc(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _closing(app_base_url: str, trigger: str) -> str:
    return (
        f"You can review your links here: {app_base_url}/my-links\n\n"
        f"You receive this email because, when you created this link, you asked to be notified {trigger}."
    )


def one_time_link_opened_email(
    recipient: Recipient, password_name: str, read_at: datetime, app_base_url: str
) -> OutgoingEmail:
    return OutgoingEmail(
        to=recipient.email,
        subject="Le Coffre: your one-time link was opened",
        body=(
            f"Hello {recipient.display_name},\n\n"
            f'The one-time link you created for "{password_name}" was opened on '
            f"{_readable_utc(read_at)}. It can no longer be used.\n\n"
            f"{_closing(app_base_url, 'when it was opened')}"
        ),
    )


def one_time_link_expired_unused_email(
    recipient: Recipient, password_name: str, expires_at: datetime, app_base_url: str
) -> OutgoingEmail:
    return OutgoingEmail(
        to=recipient.email,
        subject="Le Coffre: your one-time link expired unused",
        body=(
            f"Hello {recipient.display_name},\n\n"
            f'The one-time link you created for "{password_name}" expired on '
            f"{_readable_utc(expires_at)} without being opened.\n\n"
            f"{_closing(app_base_url, 'if it expired unused')}"
        ),
    )
