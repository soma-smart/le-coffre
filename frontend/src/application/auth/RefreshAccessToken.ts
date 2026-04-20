import type { AuthGateway } from '@/application/ports/AuthGateway'

/**
 * Refreshes the access-token cookie using the HTTP-only refresh-token
 * cookie. The gateway is the only thing that knows about cookies;
 * errors surface for the caller (customClient) to decide whether to
 * redirect to /login.
 */
export class RefreshAccessTokenUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  execute(): Promise<void> {
    return this.gateway.refreshAccessToken()
  }
}
