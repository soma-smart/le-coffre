import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'
import { isSafeInternalPath } from '@/domain/auth/loginRedirect'

/**
 * Retrieve the stashed destination, exactly once.
 *
 * Re-validated on the way out: session storage is writable by anything running
 * on the origin, so the stored value is treated as input, not as trusted state.
 */
export class ConsumeLoginRedirectUseCase {
  constructor(private readonly gateway: LoginRedirectGateway) {}

  execute(): string | null {
    const path = this.gateway.consume()
    if (!path || !isSafeInternalPath(path)) return null
    return path
  }
}
