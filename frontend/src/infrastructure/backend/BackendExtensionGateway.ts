import {
  approveExtensionPairingExtensionPairingUserCodeApprovePost,
  denyExtensionPairingExtensionPairingUserCodeDenyPost,
  getExtensionPairingExtensionPairingUserCodeGet,
  listExtensionTokensExtensionTokensGet,
  revokeAllExtensionTokensExtensionTokensDelete,
  revokeExtensionTokenExtensionTokensTokenIdDelete,
} from '@/client/sdk.gen'
import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'
import type { ConnectedExtension, ExtensionPairingDetails } from '@/domain/extension/Extension'
import {
  ConnectedExtensionNotFoundError,
  ExtensionDomainError,
  ExtensionPairingUnavailableError,
  TooManyConnectedExtensionsError,
} from '@/domain/extension/errors'

/**
 * Backend adapter for ExtensionGateway, and the only @/client touchpoint for
 * the extension feature. Translates snake_case DTOs to camelCase domain types
 * and HTTP status to domain errors at the boundary.
 */
export class BackendExtensionGateway implements ExtensionGateway {
  async getPairing(userCode: string): Promise<ExtensionPairingDetails> {
    const response = await getExtensionPairingExtensionPairingUserCodeGet({
      path: { user_code: userCode },
    })

    if (response.error || !response.data) {
      // 404 and 400 alike: the backend deliberately refuses to say which,
      // so neither does this.
      throw new ExtensionPairingUnavailableError(extractDetail(response.error) ?? undefined)
    }

    return {
      userCode: response.data.user_code,
      deviceName: response.data.device_name,
      createdAt: new Date(response.data.created_at),
      expiresAt: new Date(response.data.expires_at),
      createdFromIp: response.data.created_from_ip ?? null,
      isResolved: response.data.is_resolved,
    }
  }

  async approvePairing(userCode: string): Promise<void> {
    const response = await approveExtensionPairingExtensionPairingUserCodeApprovePost({
      path: { user_code: userCode },
    })

    if (response.error) {
      if (response.response?.status === 409) {
        throw new TooManyConnectedExtensionsError(extractDetail(response.error) ?? undefined)
      }
      throw new ExtensionPairingUnavailableError(extractDetail(response.error) ?? undefined)
    }
  }

  async denyPairing(userCode: string): Promise<void> {
    const response = await denyExtensionPairingExtensionPairingUserCodeDenyPost({
      path: { user_code: userCode },
    })

    if (response.error) {
      throw new ExtensionPairingUnavailableError(extractDetail(response.error) ?? undefined)
    }
  }

  async listConnectedExtensions(): Promise<ConnectedExtension[]> {
    const response = await listExtensionTokensExtensionTokensGet()

    if (response.error || !response.data) {
      throw new ExtensionDomainError(
        extractDetail(response.error) ?? 'Failed to load connected extensions',
      )
    }

    return response.data.tokens.map((token) => ({
      id: token.id,
      deviceName: token.device_name,
      createdAt: new Date(token.created_at),
      expiresAt: new Date(token.expires_at),
      lastUsedAt: token.last_used_at ? new Date(token.last_used_at) : null,
      revokedAt: token.revoked_at ? new Date(token.revoked_at) : null,
      createdFromIp: token.created_from_ip ?? null,
      isActive: token.is_active,
    }))
  }

  async disconnectExtension(extensionId: string): Promise<void> {
    const response = await revokeExtensionTokenExtensionTokensTokenIdDelete({
      path: { token_id: extensionId },
    })

    if (response.error) {
      if (response.response?.status === 404) {
        throw new ConnectedExtensionNotFoundError(extractDetail(response.error) ?? undefined)
      }
      throw new ExtensionDomainError(
        extractDetail(response.error) ?? 'Failed to disconnect the extension',
      )
    }
  }

  async disconnectAllExtensions(): Promise<number> {
    const response = await revokeAllExtensionTokensExtensionTokensDelete()

    if (response.error || !response.data) {
      throw new ExtensionDomainError(
        extractDetail(response.error) ?? 'Failed to disconnect the extensions',
      )
    }

    return response.data.revoked_count
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
