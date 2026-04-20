import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { buildContainer, type Container, type Ports } from '@/container'
import { InMemoryCsrfGateway } from '@/infrastructure/in_memory/InMemoryCsrfGateway'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { setContainer } from '@/plugins/container'

/**
 * Per-test setup shared by every spec that mounts a Vue component or
 * uses a Pinia setup store:
 *
 *   1. Builds a fresh Pinia instance and installs it as the active one
 *      (so stores created outside of mount() see the same registry).
 *   2. Builds the clean-architecture container, filling in in-memory
 *      fakes for any port the caller doesn't override. Each new
 *      bounded context registers a fake here so existing specs don't
 *      need to know about unrelated ports.
 *
 * Callers pass `pinia` under `global.plugins` and the container under
 * `global.provide: { [CONTAINER_KEY]: container }` when mounting.
 */
export function createTestContext(overrides: Partial<Ports> = {}): {
  pinia: Pinia
  container: Container
} {
  const pinia = createPinia()
  setActivePinia(pinia)
  const ports: Ports = {
    passwordRepository: new InMemoryPasswordRepository(),
    csrfGateway: new InMemoryCsrfGateway(),
    userRepository: new InMemoryUserRepository(),
    ...overrides,
  }
  const container = buildContainer(ports)
  // Also set the module-level fallback so Pinia stores created in
  // beforeEach (outside a mounted component) can still resolve the
  // container via useContainer(). test/setup.ts resets it in afterEach
  // so tests stay isolated.
  setContainer(container)
  return { pinia, container }
}
