from dataclasses import dataclass
from uuid import UUID


@dataclass
class ListGroupsCommand:
    include_personal: bool = True
    #: When set, keep only the groups this user owns or belongs to. Left None by
    #: the web app, which lists everything and filters in the browser; set by the
    #: extension, whose token must not be able to enumerate the whole instance.
    only_for_user_id: UUID | None = None
