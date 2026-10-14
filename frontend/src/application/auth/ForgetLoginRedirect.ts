import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'

/**
 * Drop a stashed SSO destination that will never be consumed.
 *
 * Called when the SSO callback fails: the round trip is over, nothing will
 * navigate to the stored path, and leaving it in session storage would attach
 * it to the next login attempt in this tab.
 */
export class ForgetLoginRedirectUseCase {
  constructor(private readonly gateway: LoginRedirectGateway) {}

  execute(): void {
    this.gateway.forget()
  }
}
