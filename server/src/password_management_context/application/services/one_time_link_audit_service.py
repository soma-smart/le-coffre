"""Turns bare links into rows a management table can render"""

from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    UserInfoGateway,
)
from password_management_context.application.responses import OneTimeLinkAuditItemResponse
from password_management_context.domain.entities import OneTimeLink


class OneTimeLinkAuditAssembler:
    """Adds the password name and issuer email a link does not carry itself.

    Both lookups are resolved in bulk for the whole page. Resolving them per row
    would issue one query per link, and these tables exist precisely to show
    many links at once.
    """

    def __init__(self, password_repository: PasswordRepository, user_info_gateway: UserInfoGateway):
        self.password_repository = password_repository
        self.user_info_gateway = user_info_gateway

    def assemble(self, links: list[OneTimeLink], with_emails: bool) -> list[OneTimeLinkAuditItemResponse]:
        if not links:
            return []

        names = self._password_names()
        emails = self._issuer_emails(links) if with_emails else {}

        return [
            OneTimeLinkAuditItemResponse(
                id=link.id,
                password_id=link.password_id,
                # None when the password was deleted after the link was issued.
                password_name=names.get(link.password_id),
                created_by_user_id=link.created_by_user_id,
                created_by_email=emails.get(link.created_by_user_id),
                created_at=link.created_at,
                expires_at=link.expires_at,
                read_at=link.read_at,
                revoked_at=link.revoked_at,
            )
            for link in links
        ]

    def _password_names(self) -> dict[UUID, str]:
        return {password.id: password.name for password in self.password_repository.list_all()}

    def _issuer_emails(self, links: list[OneTimeLink]) -> dict[UUID, str | None]:
        # Distinct issuers only: a page of links usually comes from a handful of
        # people, so this stays a handful of lookups rather than one per row.
        return {
            user_id: self.user_info_gateway.get_user_email(user_id)
            for user_id in {link.created_by_user_id for link in links}
        }
