/**
 * The one place HTTP becomes a domain outcome.
 *
 * Every screen switches on `AppError.kind`, never on a status code, which is
 * what keeps the popup at six screens instead of twenty.
 */
import type { ZodType } from 'zod'

import { type AppError, type Result, err, ok } from '@/domain/errors'

export interface HttpRequest {
  url: string
  method?: 'GET' | 'POST'
  body?: unknown
  bearerToken?: string | null
  signal?: AbortSignal
}

/** How long the extension waits before calling a vault unreachable. */
const REQUEST_TIMEOUT_MS = 15_000

function retryAfterSeconds(response: Response): number {
  const header = response.headers.get('Retry-After')
  if (!header) return 60

  const asSeconds = Number(header)
  if (Number.isFinite(asSeconds)) return Math.max(1, Math.round(asSeconds))

  // The header may also be an HTTP date.
  const asDate = Date.parse(header)
  if (Number.isNaN(asDate)) return 60
  return Math.max(1, Math.round((asDate - Date.now()) / 1000))
}

async function readErrorCode(response: Response): Promise<string | null> {
  try {
    const body = (await response.clone().json()) as { code?: unknown }
    return typeof body.code === 'string' ? body.code : null
  } catch {
    return null
  }
}

async function toAppError(response: Response): Promise<AppError> {
  switch (response.status) {
    case 401:
      return { kind: 'AUTH_LOST', reason: 'revoked' }
    case 403:
      return { kind: 'FORBIDDEN' }
    case 404:
      return { kind: 'NOT_FOUND' }
    case 429:
      return { kind: 'RATE_LIMITED', retryAfterSeconds: retryAfterSeconds(response) }
    case 503: {
      // Two very different 503s share this status: the vault is locked (an
      // admin must act) and the server is still running migrations (wait a
      // moment). Telling the user the wrong one wastes their time.
      const code = await readErrorCode(response)
      return code === 'starting' ? { kind: 'SERVER_STARTING' } : { kind: 'VAULT_LOCKED' }
    }
    default:
      return { kind: 'SERVER_ERROR', status: response.status }
  }
}

/** Perform a request and validate its body, turning every failure into an AppError. */
export async function request<T>(input: HttpRequest, schema: ZodType<T>): Promise<Result<T>> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(input.url, {
      method: input.method ?? 'GET',
      signal: input.signal ?? controller.signal,
      headers: {
        Accept: 'application/json',
        ...(input.body ? { 'Content-Type': 'application/json' } : {}),
        ...(input.bearerToken ? { Authorization: `Bearer ${input.bearerToken}` } : {}),
      },
      body: input.body ? JSON.stringify(input.body) : undefined,
      // Never send cookies. They would not be attached anyway (every session
      // cookie is SameSite=strict), and asking for them muddies the intent:
      // this client authenticates with a bearer token or not at all.
      credentials: 'omit',
    })
  } catch {
    // A fetch made without the host permission fails exactly like an offline
    // one, which is why callers check `permissions.contains` first.
    return err({ kind: 'NETWORK_UNREACHABLE' })
  } finally {
    clearTimeout(timeout)
  }

  if (!response.ok) {
    return err(await toAppError(response))
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return err({ kind: 'NOT_A_VAULT' })
  }

  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
    return err({
      kind: 'PROTOCOL_MISMATCH',
      detail:
        parsed.error.issues.map((issue) => issue.path.join('.')).join(', ') || 'unexpected shape',
    })
  }

  return ok(parsed.data)
}
