import { BackendCsrfGateway } from '@/infrastructure/backend/BackendCsrfGateway'
import { BackendPasswordRepository } from '@/infrastructure/backend/BackendPasswordRepository'
import { buildContainer, type Container } from '@/container'

/**
 * Production wiring. Called once in `main.ts` before `createApp(...)` is
 * mounted. It instantiates every backend adapter and feeds them to
 * `buildContainer`. Tests never call this — they build their own
 * container with in-memory fakes.
 *
 * As features migrate, each one adds its BackendXxxRepository /
 * BackendXxxGateway here.
 */
export function installProductionContainer(): Container {
  return buildContainer({
    passwordRepository: new BackendPasswordRepository(),
    csrfGateway: new BackendCsrfGateway(),
  })
}
