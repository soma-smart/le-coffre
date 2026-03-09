from typing import Protocol

from identity_access_management_context.domain.entities import SsoConfiguration


class SsoConfigurationRepository(Protocol):
    """Repository for SSO configuration persistence."""

    def save(self, config: SsoConfiguration) -> None:
        """Save or update SSO configuration."""
        ...

    def get(self) -> SsoConfiguration | None:
        """Get the current SSO configuration."""
        ...
