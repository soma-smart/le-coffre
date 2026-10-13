from datetime import datetime, timezone
from typing import Mapping

from notification_context.domain.value_objects import Recipient


def _readable_utc(iso_timestamp: str) -> str:
    moment = datetime.fromisoformat(iso_timestamp)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _closing(app_base_url: str, trigger: str) -> str:
    # No token, no secret: the email only points at the list of the user's links.
    return (
        f"You can review your links here: {app_base_url}/my-links\n\n"
        f"You receive this email because, when you created this link, you asked to be notified {trigger}."
    )


def one_time_link_read_template(recipient: Recipient, params: Mapping[str, str], app_base_url: str) -> tuple[str, str]:
    body = (
        f"Hello {recipient.display_name},\n\n"
        f'The one-time link you created for "{params["password_name"]}" was opened on '
        f"{_readable_utc(params['read_at'])}. It can no longer be used.\n\n"
        f"{_closing(app_base_url, 'when it was opened')}"
    )
    return "Le Coffre: your one-time link was opened", body


def one_time_link_expired_template(
    recipient: Recipient, params: Mapping[str, str], app_base_url: str
) -> tuple[str, str]:
    body = (
        f"Hello {recipient.display_name},\n\n"
        f'The one-time link you created for "{params["password_name"]}" expired on '
        f"{_readable_utc(params['expires_at'])} without being opened.\n\n"
        f"{_closing(app_base_url, 'if it expired unused')}"
    )
    return "Le Coffre: your one-time link expired unused", body
