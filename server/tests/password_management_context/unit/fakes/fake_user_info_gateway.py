from uuid import UUID

from password_management_context.application.gateways import PrincipalInfo


class FakeUserInfoGateway:
    def __init__(self):
        self._principals: dict[UUID, PrincipalInfo] = {}
        self._user_display_names: dict[UUID, str] = {}
        self._group_names: dict[UUID, str] = {}

    def get_principal(self, principal_id: UUID) -> PrincipalInfo | None:
        return self._principals.get(principal_id)

    def set_principal(self, principal_id: UUID, kind: str, display_name: str) -> None:
        """Helper method for tests to set up the principals acting in events"""
        self._principals[principal_id] = PrincipalInfo(kind=kind, display_name=display_name)

    def get_user_display_name(self, user_id: UUID) -> str | None:
        return self._user_display_names.get(user_id)

    def set_user_display_name(self, user_id: UUID, display_name: str) -> None:
        """Helper method for tests to set up user display names"""
        self._user_display_names[user_id] = display_name

    def get_group_name(self, group_id: UUID) -> str | None:
        return self._group_names.get(group_id)

    def set_group_name(self, group_id: UUID, name: str) -> None:
        """Helper method for tests to set up group names"""
        self._group_names[group_id] = name
