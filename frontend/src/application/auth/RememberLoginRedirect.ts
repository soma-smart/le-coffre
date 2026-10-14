import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'
import { toLoginRedirect } from '@/domain/auth/loginRedirect'

/**
 * Stash where the user should land after an SSO round trip.
 *
 * Silently keeps nothing for an unsafe value: the redirect later feeds
 * router.push, so an absolute or protocol-relative URL here would let a
 * crafted login link bounce a freshly authenticated user off-site. The value
 * is whatever the router read from `?redirect=`, an array when the parameter
 * is repeated, so it is typed as unknown and never assumed to be a string.
 */
export class RememberLoginRedirectUseCase {
  constructor(private readonly gateway: LoginRedirectGateway) {}

  execute(command: { path: unknown }): void {
    const path = toLoginRedirect(command.path)
    if (!path) return
    this.gateway.remember(path)
  }
}
