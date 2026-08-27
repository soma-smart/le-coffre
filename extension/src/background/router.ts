/**
 * Message dispatch.
 *
 * A `Record` keyed on `Request['type']` rather than a switch, so TypeScript
 * refuses to compile a request type with no handler. A missing branch in a
 * switch would only surface at runtime, as a popup that hangs.
 */
import { err, type Result } from '@/domain/errors'
import type { Request, RequestType } from '@/shared/messages'

import type { Deps } from './deps'
import { copyToClipboard } from './handlers/clipboard'
import { disconnect, getConnectionState, setVaultUrl } from './handlers/connection'
import { cancelPairing, startPairing } from './handlers/pairing'
import { listEntries, listGroups, matchEntries, selectGroup } from './handlers/vault'

type Handler = (deps: Deps, request: never) => Promise<Result<unknown>>

const HANDLERS: Record<RequestType, Handler> = {
  CONNECTION_GET_STATE: (deps) => getConnectionState(deps),
  CONNECTION_SET_VAULT_URL: (deps, request: { vaultUrl: string }) =>
    setVaultUrl(deps, request.vaultUrl),
  CONNECTION_DISCONNECT: (deps) => disconnect(deps),
  PAIRING_START: (deps) => startPairing(deps),
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
 */
export async function route(deps: Deps, message: unknown): Promise<Result<unknown>> {
  const request = message as Request
  const handler = request?.type ? HANDLERS[request.type] : undefined

  if (!handler) {
    return err({
      kind: 'PROTOCOL_MISMATCH',
      detail: `unknown request "${String((request as { type?: unknown })?.type)}"`,
    })
  }

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
