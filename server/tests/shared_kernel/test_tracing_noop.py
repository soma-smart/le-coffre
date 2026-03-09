import asyncio

from shared_kernel.application.tracing import TracedUseCase


class ConcreteUseCase(TracedUseCase):
    def execute(self, value: int) -> int:
        return value * 2


class AsyncUseCase(TracedUseCase):
    async def execute(self, value: int) -> int:
        return value * 3


def test_traced_use_case_is_noop_without_provider():
    """TracedUseCase must work correctly even without a TracerProvider configured."""
    result = ConcreteUseCase().execute(7)
    assert result == 14


def test_traced_use_case_async_is_noop_without_provider():
    result = asyncio.run(AsyncUseCase().execute(2))
    assert result == 6
