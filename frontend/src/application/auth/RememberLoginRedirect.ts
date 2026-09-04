import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'
import { isSafeInternalPath } from '@/domain/auth/loginRedirect'

/**
 * Stash where the user should land after an SSO round trip.
 *
 * Silently keeps nothing for an unsafe value: the redirect later feeds
 * router.push, so an absolute or protocol-relative URL here would let a
 * crafted login link bounce a freshly authenticated user off-site.
 */
export class RememberLoginRedirectUseCase {
  constructor(private readonly gateway: LoginRedirectGateway) {}

  execute(command: { path: string | null | undefined }): void {
    const path = command.path?.trim()
    if (!path || !isSafeInternalPath(path)) return
    this.gateway.remember(path)
  }
}
