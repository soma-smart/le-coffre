import type { PairingHandoffGateway } from '@/application/ports/PairingHandoffGateway'

/** Test-only PairingHandoffGateway. */
export class InMemoryPairingHandoffGateway implements PairingHandoffGateway {
  private code: string | null = null

  rememberPairingCode(userCode: string): void {
    this.code = userCode
  }

  recallPairingCode(): string | null {
    return this.code
  }

  forgetPairingCode(): void {
    this.code = null
  }

  /** Test helper: pre-populate as if a previous visit had stored it. */
  seed(userCode: string): this {
    this.code = userCode
    return this
  }
}
