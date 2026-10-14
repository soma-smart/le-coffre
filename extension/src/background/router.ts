/**
 * Message dispatch.
 *
 * A `Record` keyed on `Request['type']` rather than a switch, so TypeScript
 * refuses to compile a request type with no handler. A missing branch in a
 * switch would only surface at runtime, as a popup that hangs.
 */
import { err, type Result } from '@/domain/errors'
import { requestSchema } from '@/shared/messageSchemas'
import type { RequestType } from '@/shared/messages'

import type { Deps } from './deps'
import { copyToClipboard } from './handlers/clipboard'
import { disconnect, getConnectionState, setVaultUrl } from './handlers/connection'
import { cancelPairing, pollPairing, startPairing } from './handlers/pairing'
import { listEntries, listGroups, matchEntries, selectGroup } from './handlers/vault'

type Handler = (deps: Deps, request: never) => Promise<Result<unknown>>

const HANDLERS: Record<RequestType, Handler> = {
  CONNECTION_GET_STATE: (deps) => getConnectionState(deps),
  CONNECTION_SET_VAULT_URL: (deps, request: { vaultUrl: string }) =>
    setVaultUrl(deps, request.vaultUrl),
  CONNECTION_DISCONNECT: (deps) => disconnect(deps),
  PAIRING_START: (deps) => startPairing(deps),
  PAIRING_POLL: (deps) => pollPairing(deps),
  PAIRING_CANCEL: (deps) => cancelPairing(deps),
  GROUPS_LIST: (deps) => listGroups(deps),
  SETTINGS_SET_GROUP: (deps, request: { groupId: string }) => selectGroup(deps, request.groupId),
  ENTRIES_LIST: (deps, request: { groupId: string; query?: string }) =>
    listEntries(deps, request.groupId, request.query),
  ENTRIES_MATCH: (deps, request: { pageUrl: string }) => matchEntries(deps, request.pageUrl),
  CLIPBOARD_COPY: (deps, request: { entryId: string; field: 'login' | 'password' }) =>
    copyToClipboard(deps, request.entryId, request.field),
} as Record<RequestType, Handler>

/**
 * Run one request. Never throws across the message boundary: an exception here
 * would reach the popup as a bare "message port closed" with no diagnostic
 * value, so everything becomes a Result.
 *
 * The message is validated, not cast. Anything on the runtime channel reaches
 * this function, and a handler given `{ type: 'ENTRIES_LIST' }` with no
 * groupId would otherwise fail somewhere far from the cause.
 */
export async function route(deps: Deps, message: unknown): Promise<Result<unknown>> {
  const parsed = requestSchema.safeParse(message)
  if (!parsed.success) {
    const type = (message as { type?: unknown } | null)?.type
    return err({
      kind: 'PROTOCOL_MISMATCH',
      detail: typeof type === 'string' ? `malformed request "${type}"` : 'malformed request',
    })
  }

  const request = parsed.data
  const handler = HANDLERS[request.type]

  try {
    return await handler(deps, request as never)
  } catch (caught) {
    return err({
      kind: 'SERVER_ERROR',
      status: 0,
      detail: caught instanceof Error ? caught.message : 'unexpected failure',
    })
  }
}

/** Every request type has a handler. Asserted at load, not just at compile. */
export const HANDLED_REQUEST_TYPES = Object.keys(HANDLERS) as RequestType[]
