import secrets
from authentication_context.application.gateways import StateGenerationGateway


class RandomStateGenerationAdapter(StateGenerationGateway):
    def generate_state(self) -> str:
        return secrets.token_urlsafe(32)
