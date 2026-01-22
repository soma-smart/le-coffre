from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SsoConfiguration:
    """Domain entity representing SSO configuration."""

    client_id: str
    client_secret: str
    discovery_url: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    client_secret_decrypted: Optional[str] = None
    jwks_uri: Optional[str] = None
    updated_at: Optional[datetime] = None
