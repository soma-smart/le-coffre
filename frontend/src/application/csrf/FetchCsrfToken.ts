import type { CsrfGateway } from '@/application/ports/CsrfGateway'

/**
 * Fetches a fresh CSRF token from the backend and returns it. Errors
 * propagate — the presentation layer (Pinia store) catches them and
 * maps them to user-visible state / toasts.
 */
export class FetchCsrfTokenUseCase {
  constructor(private readonly gateway: CsrfGateway) {}

  execute(): Promise<string> {
    return this.gateway.fetchToken()
  }
}
