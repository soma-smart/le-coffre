import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BackendExtensionGateway } from '@/infrastructure/backend/BackendExtensionGateway'
import {
  ExtensionPairingUnavailableError,
  ExtensionServerError,
  ExtensionSessionLostError,
  TooManyConnectedExtensionsError,
} from '@/domain/extension/errors'

// The generated SDK is the adapter's only dependency; each call is a mock so
// the status-to-error mapping can be driven directly.
const { approve, deny } = vi.hoisted(() => ({ approve: vi.fn(), deny: vi.fn() }))
vi.mock('@/client/sdk.gen', () => ({
  approveExtensionPairingExtensionPairingUserCodeApprovePost: approve,
  denyExtensionPairingExtensionPairingUserCodeDenyPost: deny,
  getExtensionPairingExtensionPairingUserCodeGet: vi.fn(),
  listExtensionTokensExtensionTokensGet: vi.fn(),
  revokeAllExtensionTokensExtensionTokensDelete: vi.fn(),
  revokeExtensionTokenExtensionTokensTokenIdDelete: vi.fn(),
}))

function failure(status: number, detail?: string) {
  return { error: detail ? { detail } : {}, response: { status } }
}

describe('BackendExtensionGateway decision errors', () => {
  const gateway = new BackendExtensionGateway()

  beforeEach(() => {
    approve.mockReset()
    deny.mockReset()
  })

  it('should map 409 on approve to the device cap', async () => {
    approve.mockResolvedValue(failure(409, 'Too many connected extensions'))

    await expect(gateway.approvePairing('K7QM-3XR9')).rejects.toBeInstanceOf(
      TooManyConnectedExtensionsError,
    )
  })

  it.each([
    ['approvePairing', approve],
    ['denyPairing', deny],
  ] as const)(
    'should map 403 on %s to a lost session, asking for a reload',
    async (method, call) => {
      // Regression. Every non-409 failure used to read "invalid or expired",
      // which sends the user back to the extension to start over. A 403 is the
      // CSRF token, and starting over does not restore it; a reload does.
      call.mockResolvedValue(failure(403, 'CSRF token missing'))

      const error = await gateway[method]('K7QM-3XR9').catch((caught) => caught)

      expect(error).toBeInstanceOf(ExtensionSessionLostError)
      expect(error.message).toContain('Reload the page')
    },
  )

  it.each([
    ['approvePairing', approve, 500],
    ['approvePairing', approve, 503],
    ['denyPairing', deny, 502],
  ] as const)('should map a %s %i to "try again"', async (method, call, status) => {
    call.mockResolvedValue(failure(status, 'Internal Server Error'))

    const error = await gateway[method]('K7QM-3XR9').catch((caught) => caught)

    expect(error).toBeInstanceOf(ExtensionServerError)
    expect(error.message).toContain('try again')
  })

  it.each([400, 404])('should keep the deliberately vague wording for a %i', async (status) => {
    approve.mockResolvedValue(failure(status, 'This pairing request is invalid or has expired'))

    await expect(gateway.approvePairing('K7QM-3XR9')).rejects.toBeInstanceOf(
      ExtensionPairingUnavailableError,
    )
  })

  it('should treat a failure with no status as unavailable rather than crash', async () => {
    approve.mockResolvedValue({ error: {}, response: undefined })

    await expect(gateway.approvePairing('K7QM-3XR9')).rejects.toBeInstanceOf(
      ExtensionPairingUnavailableError,
    )
  })

  it('should resolve quietly on success', async () => {
    approve.mockResolvedValue({ data: undefined, error: undefined, response: { status: 204 } })

    await expect(gateway.approvePairing('K7QM-3XR9')).resolves.toBeUndefined()
  })
})
