from uuid import UUID

from identity_access_management_context.application.gateways import GroupUsageGateway


class FakeGroupUsageGateway(GroupUsageGateway):
    def __init__(self):
        self.group_usage = dict()

    def is_group_used(self, group_id: UUID) -> bool:
        return self.group_usage.get(group_id, False)

    def _set_usage_to_group(self, group_id):
        self.group_usage[group_id] = True
