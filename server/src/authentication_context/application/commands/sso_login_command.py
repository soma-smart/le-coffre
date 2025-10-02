from dataclasses import dataclass


@dataclass
class SsoLoginCommand:
    code: str
    redirect_uri: str | None = None
