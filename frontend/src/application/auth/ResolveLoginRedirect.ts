import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'
import { toLoginRedirect } from '@/domain/auth/loginRedirect'

/**
 * Where a password login lands.
 *
 * The password flow keeps `?redirect=` in the URL, so the destination is the
 * query value, held to the same rule as the SSO stash: the login form used to
 * push it straight to the router, which is how "/\evil.com" left the site.
 *
 * A password login also ends any SSO round trip the user started from this
 * tab and walked away from, so the stash is dropped here. Left alone it would
 * wait for the next SSO login in the same tab and send that person, possibly
 * a different one on a shared machine, to a page they never asked for.
 */
export class ResolveLoginRedirectUseCase {
  constructor(private readonly gateway: LoginRedirectGateway) {}

  execute(command: { requested: unknown }): string | null {
    this.gateway.forget()
    return toLoginRedirect(command.requested)
  }
}
