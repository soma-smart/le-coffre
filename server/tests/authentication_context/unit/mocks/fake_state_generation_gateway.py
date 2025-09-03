from authentication_context.application.gateways import StateGenerationGateway


class FakeStateGenerationGateway(StateGenerationGateway):
    def __init__(self):
        self.generation_calls = []

    def set_state(self, state: str):
        self.state_to_generate = state

    def generate_state(self) -> str:
        self.generation_calls.append(self.state_to_generate)
        return self.state_to_generate
