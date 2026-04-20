import type { CsrfGateway } from '@/application/ports/CsrfGateway'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { FetchCsrfTokenUseCase } from '@/application/csrf/FetchCsrfToken'
import { CreatePasswordUseCase } from '@/application/password/CreatePassword'
import { DeletePasswordUseCase } from '@/application/password/DeletePassword'
import { GetPasswordUseCase } from '@/application/password/GetPassword'
import { ListPasswordAccessUseCase } from '@/application/password/ListPasswordAccess'
import { ListPasswordEventsUseCase } from '@/application/password/ListPasswordEvents'
import { ListPasswordsUseCase } from '@/application/password/ListPasswords'
import { SharePasswordUseCase, UnsharePasswordUseCase } from '@/application/password/SharePassword'
import { UpdatePasswordUseCase } from '@/application/password/UpdatePassword'

/**
 * Framework-free container — holds every use case the presentation
 * layer needs. Vue imports nothing from this file; `plugins/container.ts`
 * is the only Vue-aware bridge. Tests build their own container with
 * in-memory fakes; production wires backend adapters via
 * `composition_root.ts`.
 *
 * Features are added one bounded context at a time, each extending
 * `Ports` and `Container`.
 */

export interface Ports {
  passwordRepository: PasswordRepository
  csrfGateway: CsrfGateway
}

export interface Container {
  passwords: {
    list: ListPasswordsUseCase
    get: GetPasswordUseCase
    create: CreatePasswordUseCase
    update: UpdatePasswordUseCase
    delete: DeletePasswordUseCase
    share: SharePasswordUseCase
    unshare: UnsharePasswordUseCase
    listAccess: ListPasswordAccessUseCase
    listEvents: ListPasswordEventsUseCase
  }
  csrf: {
    fetchToken: FetchCsrfTokenUseCase
  }
}

export function buildContainer(ports: Ports): Container {
  return {
    passwords: {
      list: new ListPasswordsUseCase(ports.passwordRepository),
      get: new GetPasswordUseCase(ports.passwordRepository),
      create: new CreatePasswordUseCase(ports.passwordRepository),
      update: new UpdatePasswordUseCase(ports.passwordRepository),
      delete: new DeletePasswordUseCase(ports.passwordRepository),
      share: new SharePasswordUseCase(ports.passwordRepository),
      unshare: new UnsharePasswordUseCase(ports.passwordRepository),
      listAccess: new ListPasswordAccessUseCase(ports.passwordRepository),
      listEvents: new ListPasswordEventsUseCase(ports.passwordRepository),
    },
    csrf: {
      fetchToken: new FetchCsrfTokenUseCase(ports.csrfGateway),
    },
  }
}
