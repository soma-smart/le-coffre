from dataclasses import dataclass, field

from ._response import ServiceAccountItemResponse


@dataclass(frozen=True, kw_only=True)
class RotateServiceAccountTokenResponse(ServiceAccountItemResponse):
    """Response on service account token rotation."""

    token: str = field(repr=False)
    """The new token generated for the service account."""
