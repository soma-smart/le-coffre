from dataclasses import dataclass
from datetime import datetime


@dataclass
class SsoConfiguration:
    """Domain entity representing SSO configuration."""

    client_id: str
    client_secret: str
    discovery_url: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    client_secret_decrypted: str | None = None
    jwks_uri: str | None = None
    updated_at: datetime | None = None
