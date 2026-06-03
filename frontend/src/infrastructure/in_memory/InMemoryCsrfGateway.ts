import type { CsrfGateway } from '@/application/ports/CsrfGateway'

/**
 * Test-only CsrfGateway. Seed a token with `seed(token)` or make the
 * gateway fail with `failWith(new Error(...))` to exercise the store's
 * error path. Mirrors the fake pattern used by
 * InMemoryPasswordRepository.
 */
export class InMemoryCsrfGateway implements CsrfGateway {
  private nextToken = 'in-memory-csrf-token'
  private nextError: Error | null = null

  seed(token: string): this {
    this.nextToken = token
    this.nextError = null
    return this
  }

  failWith(error: Error): this {
    this.nextError = error
    return this
  }

  async fetchToken(): Promise<string> {
    if (this.nextError) throw this.nextError
    return this.nextToken
  }
}
