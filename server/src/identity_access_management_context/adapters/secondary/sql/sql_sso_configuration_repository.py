from datetime import datetime, timezone

from sqlmodel import Session, select

from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.sso_configuration_model import SsoConfigurationTable


class SqlSsoConfigurationRepository(SQLBaseRepository, SsoConfigurationRepository):
    """SQL-based repository for SSO configuration."""

    def __init__(self, session: Session):
        super().__init__(session)

    def save(self, config: SsoConfiguration) -> None:
        """Save or update SSO configuration (always single row with id=1)."""
        existing = self._get_table_config()

        if existing:
            # Update existing configuration
            existing.client_id = config.client_id
            existing.client_secret = config.client_secret
            existing.discovery_url = config.discovery_url
            existing.authorization_endpoint = config.authorization_endpoint
            existing.token_endpoint = config.token_endpoint
            existing.userinfo_endpoint = config.userinfo_endpoint
            existing.jwks_uri = config.jwks_uri
            existing.updated_at = config.updated_at or datetime.now(timezone.utc)
            self._session.add(existing)
        else:
            # Create new configuration
            table_config = SsoConfigurationTable(
                id=1,
                client_id=config.client_id,
                client_secret=config.client_secret,
                discovery_url=config.discovery_url,
                authorization_endpoint=config.authorization_endpoint,
                token_endpoint=config.token_endpoint,
                userinfo_endpoint=config.userinfo_endpoint,
                jwks_uri=config.jwks_uri,
            )
            self._session.add(table_config)

        self.commit()

    def get(self) -> SsoConfiguration | None:
        """Get the stored SSO configuration."""
        table_config = self._get_table_config()
        if not table_config:
            return None

        return SsoConfiguration(
            client_id=table_config.client_id,
            client_secret=table_config.client_secret,
            discovery_url=table_config.discovery_url,
            authorization_endpoint=table_config.authorization_endpoint,
            token_endpoint=table_config.token_endpoint,
            userinfo_endpoint=table_config.userinfo_endpoint,
            jwks_uri=table_config.jwks_uri,
            updated_at=table_config.updated_at,
        )

    def _get_table_config(self) -> SsoConfigurationTable | None:
        """Get the configuration table row."""
        statement = select(SsoConfigurationTable).where(SsoConfigurationTable.id == 1)
        return self._session.exec(statement).first()
