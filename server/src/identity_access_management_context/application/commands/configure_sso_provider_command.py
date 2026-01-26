from dataclasses import dataclass
from shared_kernel.authentication import AuthenticatedUser


@dataclass
class ConfigureSsoProviderCommand:
    requesting_user: AuthenticatedUser
    client_id: str
    client_secret: str
    discovery_url: str
