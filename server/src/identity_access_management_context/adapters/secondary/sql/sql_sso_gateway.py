from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from urllib.parse import urlencode
import httpx
from identity_access_management_context.application.gateways import (
    SsoGateway,
    SsoUserInfo,
)
from identity_access_management_context.domain.exceptions import (
    InvalidSsoCodeException,
    InvalidSsoSettingsException,
)
from .model.sso_configuration_model import SsoConfigurationTable


class SqlSsoGateway(SsoGateway):
    """SQL-based SSO Gateway that stores configuration in database."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def get_authorize_url(self) -> str:
        """Get the OAuth authorization URL."""
        config = self._get_configuration()
        if not config:
            raise InvalidSsoSettingsException("SSO is not configured")

        # Build OAuth authorization URL
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "scope": "openid email profile",
            "redirect_uri": "http://localhost:8000/auth/sso/callback",  # Should be configurable in production
        }

        return f"{config.authorization_endpoint}?{urlencode(params)}"

    async def validate_callback(self, code: str) -> SsoUserInfo:
        """Validate OAuth callback code and return user info."""
        config = self._get_configuration()
        if not config:
            raise InvalidSsoSettingsException("SSO is not configured")

        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            try:
                token_response = await client.post(
                    config.token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                        "redirect_uri": "http://localhost:8000/auth/sso/callback",
                    },
                )
                token_response.raise_for_status()
                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise InvalidSsoCodeException("No access token in response")

            except httpx.HTTPStatusError as e:
                raise InvalidSsoCodeException(f"Token exchange failed: {str(e)}")
            except Exception as e:
                raise InvalidSsoCodeException(f"Token exchange error: {str(e)}")

        # Fetch user info using access token
        async with httpx.AsyncClient() as client:
            try:
                userinfo_response = await client.get(
                    config.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                userinfo_response.raise_for_status()
                userinfo_data = userinfo_response.json()

                # Map userinfo to SsoUserInfo
                return SsoUserInfo(
                    email=userinfo_data.get("email", ""),
                    display_name=userinfo_data.get("name", ""),
                    sso_user_id=userinfo_data.get("sub", ""),
                    sso_provider="oidc",  # Could be made configurable
                )

            except Exception as e:
                raise InvalidSsoCodeException(f"Failed to fetch user info: {str(e)}")

    async def configure_with_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> None:
        """Configure SSO with OIDC discovery."""
        # Fetch OIDC discovery document
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(discovery_url)
                response.raise_for_status()
                discovery_data = response.json()
            except Exception as e:
                raise InvalidSsoSettingsException(
                    f"Failed to fetch OIDC discovery document: {str(e)}"
                )

        # Extract required endpoints
        try:
            authorization_endpoint = discovery_data["authorization_endpoint"]
            token_endpoint = discovery_data["token_endpoint"]
            userinfo_endpoint = discovery_data["userinfo_endpoint"]
            jwks_uri = discovery_data.get("jwks_uri")
        except KeyError as e:
            raise InvalidSsoSettingsException(
                f"Missing required endpoint in discovery document: {str(e)}"
            )

        # Upsert configuration (always id=1)
        existing = self._get_configuration()
        if existing:
            # Update existing configuration
            existing.client_id = client_id
            existing.client_secret = client_secret
            existing.discovery_url = discovery_url
            existing.authorization_endpoint = authorization_endpoint
            existing.token_endpoint = token_endpoint
            existing.userinfo_endpoint = userinfo_endpoint
            existing.jwks_uri = jwks_uri
            existing.updated_at = datetime.now(timezone.utc)
            self._session.add(existing)
        else:
            # Create new configuration
            config = SsoConfigurationTable(
                id=1,
                client_id=client_id,
                client_secret=client_secret,
                discovery_url=discovery_url,
                authorization_endpoint=authorization_endpoint,
                token_endpoint=token_endpoint,
                userinfo_endpoint=userinfo_endpoint,
                jwks_uri=jwks_uri,
            )
            self._session.add(config)

        self._session.commit()

    def _get_configuration(self) -> Optional[SsoConfigurationTable]:
        """Get the stored SSO configuration."""
        statement = select(SsoConfigurationTable).where(SsoConfigurationTable.id == 1)
        return self._session.exec(statement).first()
