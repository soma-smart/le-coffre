import type { AuthGateway } from '@/application/ports/AuthGateway'

/**
 * Logs out the current browser session. The gateway handles transport
 * and cookie details; callers only orchestrate UI/session state reset.
 */
export class LogoutUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  execute(): Promise<void> {
    return this.gateway.logout()
  }
}
