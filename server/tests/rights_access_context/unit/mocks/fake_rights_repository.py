from uuid import UUID

from rights_access_context.adapters.secondary import (
    InMemoryRightsRepository,
)

from typing import Dict, Set, Tuple
from rights_access_context.application.gateways import (
    RightsRepository,
)
from rights_access_context.domain.value_objects import Permission

class FakeRightsRepository(InMemoryRightsRepository):
    pass
