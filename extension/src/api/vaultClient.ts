/**
 * Every call the extension makes. Six read endpoints and the pairing pair,
 * nothing else: the extension is read-only by construction, not by discipline.
 *
 * Constructed with a runtime base URL, since the vault is self-hosted and its
 * address is typed by the user.
 */
import type { Entry } from '@/domain/entry'
import type { AppError, Result } from '@/domain/errors'
import { err, ok } from '@/domain/errors'
import type { Group } from '@/domain/group'
import { toApiUrl } from '@/domain/vaultUrl'

import { request } from './http'
import {
  entrySchema,
  exchangePairingSchema,
  extensionSessionSchema,
  healthSchema,
  listEntriesSchema,
  listGroupsSchema,
  revealPasswordSchema,
  startPairingSchema,
  vaultStatusSchema,
} from './schemas'
import type { ExchangePairingDto, ExtensionSessionDto, StartPairingDto } from './schemas'

function toEntry(dto: typeof entrySchema._output): Entry {
  return {
    id: dto.id,
    name: dto.name,
    folder: dto.folder,
    login: dto.login,
    url: dto.url,
    groupId: dto.group_id,
    accessibleGroupIds: dto.accessible_group_ids,
    canRead: dto.can_read,
    canWrite: dto.can_write,
    accessExpiresAt: dto.access_expires_at ?? null,
  }
}

export class VaultClient {
  constructor(
    private readonly vaultUrl: string,
    private readonly bearerToken: string | null = null,
  ) {}

  /**
   * Cheap "is this actually Le Coffre" probe. Anonymous and exempt from rate
   * limiting, so it is safe to call while the user is still typing a URL.
   */
  async health(): Promise<Result<{ status: string }>> {
    const result = await request({ url: toApiUrl(this.vaultUrl, '/health') }, healthSchema)
    if (!result.ok) {
      // A 404 or a wrong shape here means something answered but it is not a
      // vault, which is a much more useful thing to tell the user.
      return result.error.kind === 'NOT_FOUND' || result.error.kind === 'PROTOCOL_MISMATCH'
        ? err({ kind: 'NOT_A_VAULT' })
        : result
    }
    return result
  }

  /** Anonymous and rate-limit exempt, so the popup can show a locked state. */
  vaultStatus(): Promise<Result<{ status: string }>> {
    return request({ url: toApiUrl(this.vaultUrl, '/vault/status') }, vaultStatusSchema)
  }

  async startPairing(codeChallenge: string, deviceName: string): Promise<Result<StartPairingDto>> {
    const result = await request(
      {
        url: toApiUrl(this.vaultUrl, '/extension/device'),
        method: 'POST',
        body: {
          code_challenge: codeChallenge,
          code_challenge_method: 'S256',
          device_name: deviceName,
        },
      },
      startPairingSchema,
    )

    // A vault too old to know about pairing answers 404 here. Saying so beats
    // an uninterpretable error, since self-hosted version skew is normal.
    if (!result.ok && result.error.kind === 'NOT_FOUND') {
      return err({
        kind: 'VAULT_TOO_OLD',
        detail: 'This vault does not support browser extensions yet',
      })
    }
    return result
  }

  exchangePairing(userCode: string, codeVerifier: string): Promise<Result<ExchangePairingDto>> {
    return request(
      {
        url: toApiUrl(this.vaultUrl, '/extension/device/exchange'),
        method: 'POST',
        body: { user_code: userCode, code_verifier: codeVerifier },
      },
      exchangePairingSchema,
    )
  }

  session(): Promise<Result<ExtensionSessionDto>> {
    return request(
      { url: toApiUrl(this.vaultUrl, '/extension/session'), bearerToken: this.bearerToken },
      extensionSessionSchema,
    )
  }

  async listGroups(): Promise<Result<Group[]>> {
    const result = await request(
      {
        url: toApiUrl(this.vaultUrl, '/groups?include_personal=true'),
        bearerToken: this.bearerToken,
      },
      listGroupsSchema,
    )
    if (!result.ok) return result

    return ok(
      result.data.groups.map((group) => ({
        id: group.id,
        name: group.name,
        isPersonal: group.is_personal,
        userId: group.user_id,
        owners: group.owners,
        members: group.members,
      })),
    )
  }

  async listEntries(): Promise<Result<Entry[]>> {
    const result = await request(
      { url: toApiUrl(this.vaultUrl, '/passwords/list'), bearerToken: this.bearerToken },
      listEntriesSchema,
    )
    if (!result.ok) return result
    return ok(result.data.map(toEntry))
  }

  /**
   * Fetch one secret.
   *
   * Every call writes a PasswordAccessedEvent in the vault's audit log, so this
   * runs only on an explicit user action. Never prefetch.
   */
  async revealPassword(entryId: string): Promise<Result<string>> {
    const result = await request(
      {
        url: toApiUrl(this.vaultUrl, `/passwords/${encodeURIComponent(entryId)}`),
        bearerToken: this.bearerToken,
      },
      revealPasswordSchema,
    )
    if (!result.ok) return result
    return ok(result.data.password)
  }
}

export type { AppError }
