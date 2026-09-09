from dataclasses import dataclass
from uuid import UUID


@dataclass
class ValidatedExtensionTokenResponse:
    """The identity behind a bearer credential.

    `roles` is deliberately absent. The caller assembles a principal with a
    fixed non-admin role instead of echoing the user's own: an admin's
    extension token would otherwise make `/passwords/list` return the names,
    logins and URLs of every secret on the instance, and that list would be
    sitting in a browser profile.
    """

    user_id: UUID
    email: str
    display_name: str
    token_id: UUID
