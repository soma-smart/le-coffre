import threading

import pytest

from vault_management_context.adapters.secondary import InMemoryVaultSessionGateway
from vault_management_context.domain.exceptions import VaultUnlockedError


def _run_concurrently(n: int, action) -> list:
    barrier = threading.Barrier(n)
    results: list = []

    def worker():
        barrier.wait()
        try:
            results.append(action())
        except VaultUnlockedError as e:
            results.append(e)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_clear_should_report_whether_a_key_was_cleared():
    gateway = InMemoryVaultSessionGateway()
    gateway.store_decrypted_key("key")

    assert gateway.clear_decrypted_key() is True
    assert gateway.clear_decrypted_key() is False


def test_given_concurrent_locks_only_one_should_clear_the_key():
    # Each successful lock publishes an event and sends the lock emails: exactly one may win.
    gateway = InMemoryVaultSessionGateway()
    gateway.store_decrypted_key("key")

    results = _run_concurrently(20, gateway.clear_decrypted_key)

    assert results.count(True) == 1


def test_given_concurrent_unlocks_only_one_should_store_the_key():
    gateway = InMemoryVaultSessionGateway()

    results = _run_concurrently(20, lambda: gateway.store_decrypted_key("key"))

    assert sum(1 for r in results if not isinstance(r, VaultUnlockedError)) == 1


def test_given_unlocked_vault_when_storing_again_should_raise():
    gateway = InMemoryVaultSessionGateway()
    gateway.store_decrypted_key("key")

    with pytest.raises(VaultUnlockedError):
        gateway.store_decrypted_key("key")
