import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'

/** Test-only LoginRedirectGateway. Seed with `seed(path)`. */
export class InMemoryLoginRedirectGateway implements LoginRedirectGateway {
  private stored: string | null = null

  seed(path: string): this {
    this.stored = path
    return this
  }

  remember(path: string): void {
    this.stored = path
  }

  consume(): string | null {
    const path = this.stored
    this.stored = null
    return path
  }
}
