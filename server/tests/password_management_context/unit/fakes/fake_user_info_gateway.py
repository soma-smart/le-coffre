from uuid import UUID


class FakeUserInfoGateway:
    def __init__(self):
        self._user_emails: dict[UUID, str] = {}
        self._user_display_names: dict[UUID, str] = {}
        self._group_names: dict[UUID, str] = {}

    def get_user_email(self, user_id: UUID) -> str | None:
        return self._user_emails.get(user_id)

    def set_user_email(self, user_id: UUID, email: str) -> None:
        """Helper method for tests to set up user emails"""
        self._user_emails[user_id] = email

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
