from typing import Dict, Any
from authentication_context.application.gateways import JWTTokenGateway


class FakeJWTTokenGateway(JWTTokenGateway):
    def __init__(self):
        self.generated_tokens = {}
        self.generation_calls = []

    async def generate_token(self, user_id: str, claims: Dict[str, Any]) -> str:
        self.generation_calls.append((user_id, claims))
        token = f"jwt_token_for_{user_id}"
        self.generated_tokens[token] = {"user_id": user_id, **claims}
        return token

    async def validate_token(self, token: str) -> Dict[str, Any]:
        if token in self.generated_tokens:
            return self.generated_tokens[token]
        return {}
