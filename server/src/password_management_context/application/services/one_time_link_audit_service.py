"""Turns bare links into rows a management table can render"""

from uuid import UUID

from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
    PasswordRepository,
    UserInfoGateway,
)
from password_management_context.application.responses import OneTimeLinkAuditItemResponse
from password_management_context.domain.entities import OneTimeLink


class OneTimeLinkAuditAssembler:
    """Adds the context a bare link does not carry: which password it points at,
    which group owns that password, and who issued it.

    Every lookup is resolved in bulk for the whole page. Resolving them per row
    would issue several queries per link, and these tables exist precisely to
    show many links at once.
    """

    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        user_info_gateway: UserInfoGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.user_info_gateway = user_info_gateway

    def assemble(self, links: list[OneTimeLink], with_issuers: bool) -> list[OneTimeLinkAuditItemResponse]:
        if not links:
            return []

        names = self._password_names()
        groups = self._owning_group_names(links)
        issuers = self._issuer_display_names(links) if with_issuers else {}

        return [
            OneTimeLinkAuditItemResponse(
                id=link.id,
                password_id=link.password_id,
                # None when the password was deleted after the link was issued.
                password_name=names.get(link.password_id),
                group_name=groups.get(link.password_id),
                created_by_user_id=link.created_by_user_id,
                created_by_display_name=issuers.get(link.created_by_user_id),
                created_at=link.created_at,
                expires_at=link.expires_at,
                read_at=link.read_at,
                revoked_at=link.revoked_at,
            )
            for link in links
        ]

    def _password_names(self) -> dict[UUID, str]:
        return {password.id: password.name for password in self.password_repository.list_all()}

    def _owning_group_names(self, links: list[OneTimeLink]) -> dict[UUID, str | None]:
        """Resolve each password's owning group, then that group's name.

        One bulk permissions read for every password on the page, then one name
        lookup per distinct group. A password owned by several groups is not a
        thing here: exactly one holds ownership.
        """
        password_ids = list({link.password_id for link in links})
        permissions = self.password_permissions_repository.list_all_permissions_for_bulk(password_ids)

        owner_group_by_password: dict[UUID, UUID] = {}
        for password_id, group_permissions in permissions.items():
            for group_id, (is_owner, _) in group_permissions.items():
                if is_owner:
                    owner_group_by_password[password_id] = group_id
                    break

        group_names = {
            group_id: self.user_info_gateway.get_group_name(group_id)
            for group_id in set(owner_group_by_password.values())
        }
        return {password_id: group_names.get(group_id) for password_id, group_id in owner_group_by_password.items()}

    def _issuer_display_names(self, links: list[OneTimeLink]) -> dict[UUID, str | None]:
        # Distinct issuers only: a page of links usually comes from a handful of
        # people, so this stays a handful of lookups rather than one per row.
        return {
            user_id: self.user_info_gateway.get_user_display_name(user_id)
            for user_id in {link.created_by_user_id for link in links}
        }
