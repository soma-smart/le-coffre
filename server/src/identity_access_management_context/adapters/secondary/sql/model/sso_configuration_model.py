from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class SsoConfigurationTable(SQLModel, table=True):
    __tablename__: str = "SsoConfigurationTable"

    id: int = Field(default=1, primary_key=True)  # Always 1 - single row
    client_id: str = Field(description="OAuth client ID", nullable=False)
    client_secret: str = Field(description="OAuth client secret", nullable=False)
    discovery_url: str = Field(description="OIDC discovery URL", nullable=False)
    authorization_endpoint: str = Field(
        description="OAuth authorization endpoint", nullable=False
    )
    token_endpoint: str = Field(description="OAuth token endpoint", nullable=False)
    userinfo_endpoint: str = Field(
        description="OAuth userinfo endpoint", nullable=False
    )
    jwks_uri: Optional[str] = Field(
        description="JWKS URI for token validation", nullable=True, default=None
    )
    updated_at: datetime = Field(
        description="Last update timestamp",
        nullable=False,
        default_factory=lambda: datetime.now(timezone.utc),
    )
