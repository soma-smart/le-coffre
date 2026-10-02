import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'
import {
  isActive,
  type CreatedServiceAccount,
  type RotatedServiceAccountToken,
  type ServiceAccount,
  type ServiceAccountPage,
} from '@/domain/serviceAccount/ServiceAccount'
import {
  ServiceAccountAlreadyRevokedError,
  ServiceAccountNotFoundError,
  ServiceAccountNotOwnerError,
  TooManyActiveServiceAccountsError,
} from '@/domain/serviceAccount/errors'

/**
 * Test double for ServiceAccountRepository. Enforces the same rules as the real
 * backend — the per-group cap, the refusal to touch a revoked account, and a
 * rotation that changes only the token — so component and use-case tests
 * exercise real behaviour rather than a permissive stub.
 */
export class InMemoryServiceAccountRepository implements ServiceAccountRepository {
  private accounts = new Map<string, ServiceAccount>()
  private maxActive = 3
  private deniedGroups = new Set<string>()
  private creator = { id: 'user-1', name: 'Ada Owner' }
  private idGenerator: () => string = () => `account-${this.accounts.size + 1}`
  private tokenGenerator: () => string = () => `token-${this.accounts.size + 1}`

  seed(account: ServiceAccount): this {
    this.accounts.set(account.id, account)
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

  withMaxActive(max: number): this {
    this.maxActive = max
    return this
  }

  /** Test-only: whose name creation records as the creator. */
  createdBy(id: string, name: string | null): this {
    this.creator = { id, name: name ?? '' }
    return this
  }

  /**
   * Test-only: this group answers as the server does for someone who does not
   * own it. Behavioural rather than a generic error injector, so a test reads
   * as "not an owner of this group" instead of "make the next call throw".
   */
  denyGroup(groupId: string): this {
    this.deniedGroups.add(groupId)
    return this
  }

  async create(groupId: string, name: string): Promise<CreatedServiceAccount> {
    this.ensureCanManage(groupId)
    const active = this.accountsOf(groupId).filter(isActive).length
    if (active >= this.maxActive) {
      throw new TooManyActiveServiceAccountsError(
        `This group already has ${active} active service accounts (maximum ${this.maxActive}). ` +
          'Revoke one before creating another.',
      )
    }
    const id = this.idGenerator()
    const token = this.tokenGenerator()
    this.accounts.set(id, {
      id,
      groupId,
      name,
      createdByUserId: this.creator.id,
      createdByUserName: this.creator.name || null,
      createdAt: new Date().toISOString(),
      revokedAt: null,
    })
    return { id, groupId, name, token }
  }

  async listForGroup(groupId: string): Promise<ServiceAccountPage> {
    this.ensureCanManage(groupId)
    const accounts = this.accountsOf(groupId)
    return {
      accounts,
      active: accounts.filter(isActive).length,
      maxActive: this.maxActive,
    }
  }

  async rotate(serviceAccountId: string): Promise<RotatedServiceAccountToken> {
    const account = this.usableAccount(serviceAccountId)
    // Only the token changes: the entry keeps its name, group and creation facts.
    return { id: account.id, token: this.tokenGenerator() }
  }

  async revoke(serviceAccountId: string): Promise<void> {
    const account = this.usableAccount(serviceAccountId)
    this.accounts.set(account.id, { ...account, revokedAt: new Date().toISOString() })
  }

  private accountsOf(groupId: string): ServiceAccount[] {
    // Newest first, undated last, as the server orders them.
    const accounts = [...this.accounts.values()].filter((account) => account.groupId === groupId)
    const dated = accounts.filter((account) => account.createdAt !== null)
    const undated = accounts.filter((account) => account.createdAt === null)
    dated.sort((left, right) => (left.createdAt! < right.createdAt! ? 1 : -1))
    return [...dated, ...undated]
  }

  private ensureCanManage(groupId: string): void {
    if (this.deniedGroups.has(groupId)) throw new ServiceAccountNotOwnerError()
  }

  private usableAccount(serviceAccountId: string): ServiceAccount {
    const account = this.accounts.get(serviceAccountId)
    if (!account) throw new ServiceAccountNotFoundError()
    this.ensureCanManage(account.groupId)
    if (!isActive(account)) throw new ServiceAccountAlreadyRevokedError()
    return account
  }
}
