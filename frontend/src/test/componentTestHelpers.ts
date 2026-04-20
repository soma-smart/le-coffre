import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { buildContainer, type Container, type Ports } from '@/container'

/**
 * Per-test setup shared by every spec that mounts a Vue component or
 * uses a Pinia setup store:
 *
 *   1. Builds a fresh Pinia instance and installs it as the active one
 *      (so stores created outside of mount() see the same registry).
 *   2. Builds the clean-architecture container from caller-supplied
 *      ports (in-memory fakes, stubs, spies — whatever the test needs).
 *
 * Callers then pass `pinia` under `global.plugins` and the container
 * under `global.provide: { [CONTAINER_KEY]: container }` when mounting
 * — that's the canonical way Vue Test Utils + Pinia wire a test app.
 */
export function createTestContext(ports: Ports): { pinia: Pinia; container: Container } {
  const pinia = createPinia()
  setActivePinia(pinia)
  const container = buildContainer(ports)
  return { pinia, container }
}
