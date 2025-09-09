from .access_result import AccessResult, Granted
from .access_controller import AccessController
from .exceptions import AccessDeniedError

# AccessController provides unified access control (both check and grant operations)
__all__ = ["AccessController", "AccessDeniedError", "AccessResult", "Granted"]
