from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from identity_access_management_context.adapters.primary.fastapi.app_dependencies import (
    get_configure_sso_provider_usecase,
)

from identity_access_management_context.application.use_cases import ConfigureSsoProviderUseCase
from identity_access_management_context.domain.exceptions import InvalidSsoSettingsException


router = APIRouter(prefix="/auth", tags=["Authentication"])


class ConfigureSsoProviderRequest(BaseModel):
    """Configure SSO provider with OpenID Connect auto-discovery."""

    client_id: str = Field(..., description="Client ID OAuth2")
    client_secret: str = Field(..., description="Client secret OAuth2")
    discovery_url: str = Field(
        ...,
        description="OpenID Connect discovery URL (.well-known/openid_configuration)",
        examples=[
            "https://accounts.google.com/.well-known/openid_configuration",
            "https://login.microsoftonline.com/common/.well-known/openid_configuration",
            "https://keycloak.example.com/realms/myrealm/.well-known/openid_configuration",
        ],
    )


@router.post(
    "/sso/configure",
    status_code=200,
    summary="Configure SSO provider with OpenID Connect Discovery",
)
async def configure_sso_provider(
    request: ConfigureSsoProviderRequest,
    usecase: ConfigureSsoProviderUseCase = Depends(get_configure_sso_provider_usecase),
):
    """
    Configure an SSO provider via OpenID Connect auto-discovery.

    **Simplified configuration with only 3 parameters:**

    ```json
    {
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "discovery_url": "https://provider.com/.well-known/openid_configuration"
    }
    ```

    **Example discovery URLs for popular providers:**

    - **Google**: `https://accounts.google.com/.well-known/openid_configuration`
    - **Microsoft**: `https://login.microsoftonline.com/{tenant}/.well-known/openid_configuration`
    - **Keycloak**: `https://keycloak.example.com/realms/{realm}/.well-known/openid_configuration`
    - **Auth0**: `https://{domain}.auth0.com/.well-known/openid_configuration`
    - **Okta**: `https://{domain}.okta.com/.well-known/openid_configuration`

    Auto-discovery retrieves all necessary endpoints from the OpenID Connect configuration URL,
    ensuring compatibility with the standard.
    """
    try:
        await usecase.execute(
            client_id=request.client_id,
            client_secret=request.client_secret,
            discovery_url=request.discovery_url,
        )

    except InvalidSsoSettingsException as e:
        raise HTTPException(status_code=400, detail=str(e))
