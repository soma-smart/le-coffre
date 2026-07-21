import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import {
  isActive,
  type AuditedOneTimeLink,
  type AuditedOneTimeLinkPage,
  type CreatedOneTimeLink,
  type OneTimeLink,
  type OneTimeLinkPage,
  type RevealedSecret,
} from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkUnusableError } from '@/domain/oneTimeLink/errors'

interface SeededSecret {
  token: string
  secret: RevealedSecret
}

/**
 * Test double for OneTimeLinkRepository. Enforces the same single-use rule as
 * the real backend so component and use-case tests exercise real behaviour.
 */
export class InMemoryOneTimeLinkRepository implements OneTimeLinkRepository {
  private links = new Map<string, OneTimeLink>()
  private secrets = new Map<string, RevealedSecret>()
  private pageSize = 10
  private maxActive = 5
  private currentUserId = 'user-1'
  private idGenerator: () => string = () => `link-${this.links.size + 1}`
  private tokenGenerator: () => string = () => `token-${this.links.size + 1}`

  /** Test-only: whose links `listMine` should return. */
  actingAs(userId: string): this {
    this.currentUserId = userId
    return this
  }

  seed(link: OneTimeLink): this {
    this.links.set(link.id, link)
    return this
  }

  /** Registers a token that `consume` will resolve to the given secret. */
  seedSecret({ token, secret }: SeededSecret): this {
    this.secrets.set(token, secret)
    return this
  }

  useIdGenerator(fn: () => string): this {
    this.idGenerator = fn
    return this
  }

  useTokenGenerator(fn: () => string): this {
    this.tokenGenerator = fn
    return this
  }

  async create(passwordId: string, lifetimeSeconds?: number): Promise<CreatedOneTimeLink> {
    const id = this.idGenerator()
    const token = this.tokenGenerator()
    const now = new Date()
    const expiresAt = new Date(now.getTime() + (lifetimeSeconds ?? 86400) * 1000)
    this.links.set(id, {
      id,
      passwordId,
      createdByUserId: 'user-1',
      createdAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
      readAt: null,
      revokedAt: null,
    })
    return { id, token, expiresAt: expiresAt.toISOString() }
  }

  async listForPassword(passwordId: string, includeInactive = false): Promise<OneTimeLinkPage> {
    const all = [...this.links.values()].filter((link) => link.passwordId === passwordId)
    const activeLinks = all.filter((link) => isActive(link))
    // Mirrors the server: filter first, then take the newest, then cap. Slicing
    // before filtering would hide an active link behind newer spent ones.
    const source = includeInactive ? all : activeLinks
    const links = [...source].reverse().slice(0, this.pageSize)
    return { links, total: all.length, active: activeLinks.length, maxActive: this.maxActive }
  }

  /** Test-only: what password name and issuer email the audit pages should show. */
  private passwordNames = new Map<string, string>()
  private issuerNames = new Map<string, string>()
  private groupNames = new Map<string, string>()

  seedPasswordName(passwordId: string, name: string): this {
    this.passwordNames.set(passwordId, name)
    return this
  }

  seedIssuerName(userId: string, displayName: string): this {
    this.issuerNames.set(userId, displayName)
    return this
  }

  seedGroupName(passwordId: string, groupName: string): this {
    this.groupNames.set(passwordId, groupName)
    return this
  }

  private audited(link: OneTimeLink, withIssuers: boolean): AuditedOneTimeLink {
    return {
      ...link,
      passwordName: this.passwordNames.get(link.passwordId) ?? null,
      groupName: this.groupNames.get(link.passwordId) ?? null,
      createdByDisplayName: withIssuers
        ? (this.issuerNames.get(link.createdByUserId) ?? null)
        : null,
    }
  }

  private auditPage(
    source: OneTimeLink[],
    includeInactive: boolean,
    withIssuers: boolean,
  ): AuditedOneTimeLinkPage {
    // Mirrors the server: filter first, then take the newest, then cap. Filtering
    // after truncation would hide an old live link behind newer spent ones.
    const matching = includeInactive ? source : source.filter((link) => isActive(link))
    const links = [...matching].reverse().slice(0, this.pageSize)
    return { links: links.map((link) => this.audited(link, withIssuers)), total: matching.length }
  }

  async listAll(includeInactive = false): Promise<AuditedOneTimeLinkPage> {
    return this.auditPage([...this.links.values()], includeInactive, true)
  }

  async listMine(includeInactive = false): Promise<AuditedOneTimeLinkPage> {
    const mine = [...this.links.values()].filter(
      (link) => link.createdByUserId === this.currentUserId,
    )
    return this.auditPage(mine, includeInactive, false)
  }

  async revokeAsAdmin(linkId: string): Promise<void> {
    return this.revoke(linkId)
  }

  async revokeAllForUser(userId: string): Promise<number> {
    let revoked = 0
    for (const [id, link] of this.links) {
      // An already-read link keeps its trail rather than being marked revoked.
      if (link.createdByUserId !== userId || link.readAt || link.revokedAt) continue
      this.links.set(id, { ...link, revokedAt: new Date().toISOString() })
      revoked += 1
    }
    return revoked
  }

  async revoke(linkId: string): Promise<void> {
    const link = this.links.get(linkId)
    if (!link || link.readAt || link.revokedAt) throw new OneTimeLinkUnusableError()
    this.links.set(linkId, { ...link, revokedAt: new Date().toISOString() })
  }

  async consume(token: string): Promise<RevealedSecret> {
    const secret = this.secrets.get(token)
    if (!secret) throw new OneTimeLinkUnusableError()
    // Single use: the token is spent the moment it resolves.
    this.secrets.delete(token)
    return secret
  }
}
