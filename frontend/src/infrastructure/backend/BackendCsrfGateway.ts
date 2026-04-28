import { getCsrfTokenAuthCsrfTokenGet } from '@/client/sdk.gen'
import type { CsrfGateway } from '@/application/ports/CsrfGateway'
import { CsrfTokenEmptyError, CsrfTokenUnavailableError } from '@/domain/csrf/errors'

/**
 * Backend adapter for CsrfGateway. Wraps the SDK's
 * getCsrfTokenAuthCsrfTokenGet and extracts the token, translating
 * transport failures into domain-level errors. Only @/client touchpoint
 * for the CSRF context.
 */
export class BackendCsrfGateway implements CsrfGateway {
  async fetchToken(): Promise<string> {
    const response = await getCsrfTokenAuthCsrfTokenGet()

    if (response.error) {
      const detail = extractDetail(response.error)
      throw new CsrfTokenUnavailableError(detail ?? undefined)
    }

    if (!response.data?.csrf_token) {
      throw new CsrfTokenEmptyError()
    }

    return response.data.csrf_token
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
