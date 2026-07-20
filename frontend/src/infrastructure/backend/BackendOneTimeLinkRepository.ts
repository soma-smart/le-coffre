import {
  consumeOneTimeLinkOneTimeLinksConsumePost,
  createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost,
  listOneTimeLinksPasswordsPasswordIdOneTimeLinksGet,
  revokeOneTimeLinkOneTimeLinksLinkIdDelete,
} from '@/client/sdk.gen'
import type { OneTimeLinkSummary } from '@/client/types.gen'
import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type {
  CreatedOneTimeLink,
  OneTimeLink,
  OneTimeLinkPage,
  RevealedSecret,
} from '@/domain/oneTimeLink/OneTimeLink'
import {
  OneTimeLinkDomainError,
  OneTimeLinkNotOwnerError,
  TooManyActiveOneTimeLinksError,
  OneTimeLinkUnusableError,
  OneTimeLinkVaultLockedError,
} from '@/domain/oneTimeLink/errors'

/**
 * Backend adapter for OneTimeLinkRepository. Maps snake_case DTOs to camelCase
 * domain objects and translates HTTP status codes into domain errors.
 */
export class BackendOneTimeLinkRepository implements OneTimeLinkRepository {
  async create(passwordId: string, lifetimeSeconds?: number): Promise<CreatedOneTimeLink> {
    const response = await createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost({
      path: { password_id: passwordId },
      body: { lifetime_seconds: lifetimeSeconds ?? null },
    })
    throwOnOwnerError(response.error, response.response?.status)
    if (!response.data) throw new OneTimeLinkDomainError('Empty response from create one-time link')
    return {
      id: response.data.id,
      token: response.data.token,
      expiresAt: response.data.expires_at,
    }
  }

  async listForPassword(passwordId: string, includeInactive = false): Promise<OneTimeLinkPage> {
    const response = await listOneTimeLinksPasswordsPasswordIdOneTimeLinksGet({
      path: { password_id: passwordId },
      query: { include_inactive: includeInactive },
    })
    throwOnOwnerError(response.error, response.response?.status)
    return {
      links: (response.data?.links ?? []).map(toOneTimeLink),
      total: response.data?.total ?? 0,
      active: response.data?.active ?? 0,
      maxActive: response.data?.max_active ?? 0,
    }
  }

  async revoke(linkId: string): Promise<void> {
    const response = await revokeOneTimeLinkOneTimeLinksLinkIdDelete({
      path: { link_id: linkId },
    })
    throwOnOwnerError(response.error, response.response?.status)
  }

  async consume(token: string): Promise<RevealedSecret> {
    const response = await consumeOneTimeLinkOneTimeLinksConsumePost({ body: { token } })
    const status = response.response?.status
    if (response.error) {
      // 404 covers unknown, expired, spent and revoked alike; the backend keeps
      // them indistinguishable on purpose, so we do not guess between them.
      if (status === 404) throw new OneTimeLinkUnusableError()
      if (status === 503) throw new OneTimeLinkVaultLockedError()
      throw new OneTimeLinkDomainError(extractDetail(response.error) ?? 'Could not open this link')
    }
    if (!response.data) throw new OneTimeLinkUnusableError()
    return {
      name: response.data.name,
      password: response.data.password,
      login: response.data.login ?? null,
      url: response.data.url ?? null,
    }
  }
}

function throwOnOwnerError(error: unknown, status: number | undefined): void {
  if (!error) return
  if (status === 403) throw new OneTimeLinkNotOwnerError()
  if (status === 409) throw new TooManyActiveOneTimeLinksError(extractDetail(error))
  throw new OneTimeLinkDomainError(extractDetail(error) ?? 'One-time link operation failed')
}

function toOneTimeLink(dto: OneTimeLinkSummary): OneTimeLink {
  return {
    id: dto.id,
    passwordId: dto.password_id,
    createdByUserId: dto.created_by_user_id,
    createdAt: dto.created_at,
    expiresAt: dto.expires_at,
    readAt: dto.read_at ?? null,
    revokedAt: dto.revoked_at ?? null,
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
