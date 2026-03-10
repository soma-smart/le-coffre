from datetime import datetime
from uuid import UUID

from password_management_context.application.gateways import PasswordEventRepository


class PasswordTimestampService:
    """Application service for retrieving password timestamps from events"""

    def __init__(self, repository: PasswordEventRepository):
        self.repository = repository

    def get_timestamps(self, password_id: UUID) -> tuple[datetime, datetime]:
        """Get creation and last password update timestamps for a password.

        Returns:
            tuple of (created_at, last_password_updated_at)
            - created_at: When the password was created
            - last_password_updated_at: When the password value was last changed
              (defaults to created_at if never updated)

        Raises:
            RuntimeError: If no PasswordCreatedEvent exists for the password
        """
        creation_events = self.repository.list_events(
            password_id=password_id,
            event_types=["PasswordCreatedEvent"],
        )
        if not creation_events:
            raise RuntimeError(f"No PasswordCreatedEvent found for password {password_id}")

        created_at = self._parse_occurred_on(creation_events[0]["occurred_on"])

        update_events = self.repository.list_events(
            password_id=password_id,
            event_types=["PasswordUpdatedEvent"],
        )
        last_password_updated_at = self._find_last_password_update(update_events, created_at)

        return created_at, last_password_updated_at

    def get_timestamps_bulk(self, password_ids: list[UUID]) -> dict[UUID, tuple[datetime, datetime]]:
        """Get timestamps for multiple passwords efficiently.

        Returns:
            dict mapping password_id to (created_at, last_password_updated_at)

        Raises:
            RuntimeError: If any password is missing a PasswordCreatedEvent
        """
        if not password_ids:
            return {}

        all_events = self.repository.list_events_bulk(
            password_ids=password_ids,
            event_types=["PasswordCreatedEvent", "PasswordUpdatedEvent"],
        )

        events_by_password = self._group_events_by_password(all_events)

        result: dict[UUID, tuple[datetime, datetime]] = {}
        for password_id in password_ids:
            password_events = events_by_password.get(password_id, [])
            created_at = self._extract_creation_date(password_events)
            if created_at is None:
                raise RuntimeError(f"No PasswordCreatedEvent found for password {password_id}")
            last_password_updated_at = self._find_last_password_update(password_events, created_at)
            result[password_id] = (created_at, last_password_updated_at)

        return result

    def _parse_occurred_on(self, occurred_on: datetime | str) -> datetime:
        """Parse occurred_on field which can be datetime or ISO string"""
        if isinstance(occurred_on, str):
            return datetime.fromisoformat(occurred_on)
        return occurred_on

    def _group_events_by_password(self, all_events: list[dict]) -> dict[UUID, list[dict]]:
        """Group events by password_id"""
        events_by_password: dict[UUID, list[dict]] = {}
        for event in all_events:
            password_id = event["password_id"]
            if isinstance(password_id, str):
                password_id = UUID(password_id)
            if password_id not in events_by_password:
                events_by_password[password_id] = []
            events_by_password[password_id].append(event)
        return events_by_password

    def _extract_creation_date(self, events: list[dict]) -> datetime | None:
        """Extract creation date from PasswordCreatedEvent in events list"""
        for event in events:
            if event["event_type"] == "PasswordCreatedEvent":
                return self._parse_occurred_on(event["occurred_on"])
        return None

    def _find_last_password_update(self, events: list[dict], default_date: datetime) -> datetime:
        """Find the most recent password update event (where password value changed)

        Returns default_date if no password update events found
        """
        for event in events:
            if event["event_type"] == "PasswordUpdatedEvent":
                if event["event_data"].get("has_password_changed", False):
                    return self._parse_occurred_on(event["occurred_on"])
        return default_date
