import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import {
  isActive,
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
  private idGenerator: () => string = () => `link-${this.links.size + 1}`
  private tokenGenerator: () => string = () => `token-${this.links.size + 1}`

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
