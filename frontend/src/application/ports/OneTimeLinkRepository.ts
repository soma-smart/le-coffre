import type {
  CreatedOneTimeLink,
  OneTimeLinkPage,
  RevealedSecret,
} from '@/domain/oneTimeLink/OneTimeLink'

export interface OneTimeLinkRepository {
  create(passwordId: string, lifetimeSeconds?: number): Promise<CreatedOneTimeLink>
  /** Returns only redeemable links unless `includeInactive` is set. */
  listForPassword(passwordId: string, includeInactive?: boolean): Promise<OneTimeLinkPage>
  revoke(linkId: string): Promise<void>
  /** Anonymous: consumes the link and returns the secret. Single use. */
  consume(token: string): Promise<RevealedSecret>
}
