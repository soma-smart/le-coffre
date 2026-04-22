import { BackendAuthGateway } from '@/infrastructure/backend/BackendAuthGateway'
import { BackendCsrfGateway } from '@/infrastructure/backend/BackendCsrfGateway'
import { BackendGroupRepository } from '@/infrastructure/backend/BackendGroupRepository'
import { BackendPasswordRepository } from '@/infrastructure/backend/BackendPasswordRepository'
import { BackendUserRepository } from '@/infrastructure/backend/BackendUserRepository'
import { BackendVaultRepository } from '@/infrastructure/backend/BackendVaultRepository'
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
    userRepository: new BackendUserRepository(),
    groupRepository: new BackendGroupRepository(),
    vaultRepository: new BackendVaultRepository(),
    authGateway: new BackendAuthGateway(),
  })
}
