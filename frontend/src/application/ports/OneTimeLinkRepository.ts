import type {
  AuditedOneTimeLinkPage,
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
  /** Every link in the vault. Admin only. */
  listAll(includeInactive?: boolean): Promise<AuditedOneTimeLinkPage>
  /** The links the caller issued, wherever they point. */
  listMine(includeInactive?: boolean): Promise<AuditedOneTimeLinkPage>
  /** Revoke any link, regardless of who issued it. Admin only. */
  revokeAsAdmin(linkId: string): Promise<void>
  /** Cut every live link one user issued, returning how many were cut. Admin only. */
  revokeAllForUser(userId: string): Promise<number>
}
