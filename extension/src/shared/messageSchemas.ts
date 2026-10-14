/**
 * Runtime shapes for the messages in messages.ts.
 *
 * A message listener receives whatever was sent, and `chrome.runtime` delivers
 * from every page of this extension. The service worker and the offscreen
 * document validate what they receive rather than cast it, so a malformed
 * request answers with a typed error instead of a handler throwing on
 * `undefined.length` deep inside a call that has already hit the network.
 *
 * Types stay in messages.ts, with their documentation; the two assertions at
 * the bottom keep this file and that one in step in both directions.
 */
import { z } from 'zod'

import type { OffscreenReply, OffscreenRequest, Request } from './messages'

export const requestSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('CONNECTION_GET_STATE') }),
  z.object({ type: z.literal('CONNECTION_SET_VAULT_URL'), vaultUrl: z.string() }),
  z.object({ type: z.literal('CONNECTION_DISCONNECT') }),
  z.object({ type: z.literal('PAIRING_START') }),
  z.object({ type: z.literal('PAIRING_POLL') }),
  z.object({ type: z.literal('PAIRING_CANCEL') }),
  z.object({ type: z.literal('GROUPS_LIST') }),
  z.object({ type: z.literal('SETTINGS_SET_GROUP'), groupId: z.string() }),
  z.object({ type: z.literal('ENTRIES_LIST'), groupId: z.string(), query: z.string().optional() }),
  z.object({ type: z.literal('ENTRIES_MATCH'), pageUrl: z.string() }),
  z.object({
    type: z.literal('CLIPBOARD_COPY'),
    entryId: z.string(),
    field: z.enum(['login', 'password']),
  }),
])

/**
 * The port between the service worker and the offscreen document. A named
 * port rather than `runtime.sendMessage`: a broadcast reaches every listener
 * in the extension, and OFFSCREEN_COPY carries the secret.
 */
export const OFFSCREEN_PORT_NAME = 'le-coffre-clipboard'

export const offscreenRequestSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('OFFSCREEN_COPY'),
    value: z.string(),
    clearAfterSeconds: z.number().positive().nullable(),
  }),
  z.object({ type: z.literal('OFFSCREEN_CLEAR') }),
])

export const offscreenReplySchema = z.discriminatedUnion('ok', [
  z.object({ ok: z.literal(true) }),
  z.object({ ok: z.literal(false), error: z.enum(['MALFORMED_REQUEST', 'COPY_FAILED']) }),
])

// Both directions, so a request type added to messages.ts without a schema
// here fails to compile, and so does a schema for a type that does not exist.
// `Expect` is what makes a mismatch an error: a bare conditional type that
// resolves to `never` would satisfy any constraint and fail nothing.
type Mutual<A, B> = [A] extends [B] ? ([B] extends [A] ? true : false) : false
type Expect<T extends true> = T
export type RequestSchemaMatches = Expect<Mutual<z.infer<typeof requestSchema>, Request>>
export type OffscreenRequestSchemaMatches = Expect<
  Mutual<z.infer<typeof offscreenRequestSchema>, OffscreenRequest>
>
export type OffscreenReplySchemaMatches = Expect<
  Mutual<z.infer<typeof offscreenReplySchema>, OffscreenReply>
>
