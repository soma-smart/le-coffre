/**
 * The popup ⟷ service-worker protocol.
 *
 * The popup never calls the API directly (enforced by eslint: `popup/**` may
 * not import `api/**`). Everything crosses this boundary, for three reasons:
 * the popup is destroyed on any outside click and would abort an in-flight
 * reveal *after* the server has already written its audit event; a future
 * autofill content script physically cannot fetch cross-origin under Chrome's
 * post-85 CORS rules; and rate-limit bookkeeping needs one owner.
 */
import type { Result } from '@/domain/errors'

/** Metadata for one vault entry. Never carries a secret. */
export interface EntrySummary {
  id: string
  name: string
  folder: string
  login: string | null
  url: string | null
  groupId: string
  accessibleGroupIds: string[]
  canRead: boolean
  canWrite: boolean
  accessExpiresAt: string | null
}

export interface GroupSummary {
  id: string
  name: string
  isPersonal: boolean
  isOwner: boolean
}

export type ConnectionState =
  | { status: 'unconfigured' }
  | { status: 'permission-missing'; vaultUrl: string }
  | { status: 'unpaired'; vaultUrl: string }
  | {
      status: 'pairing'
      vaultUrl: string
      userCode: string
      expiresAt: string
      /** Server-chosen cadence. The pairing bucket is sized for it; see config.py. */
      pollIntervalSeconds: number
    }
  | {
      status: 'ready'
      vaultUrl: string
      email: string
      displayName: string
      groupId: string | null
    }
  | { status: 'locked'; vaultUrl: string }

export type Request =
  | { type: 'CONNECTION_GET_STATE' }
  | { type: 'CONNECTION_SET_VAULT_URL'; vaultUrl: string }
  | { type: 'CONNECTION_DISCONNECT' }
  | { type: 'PAIRING_START' }
  /**
   * Drive one exchange attempt now, rather than waiting for the alarm.
   *
   * The service worker's alarm is the safety net for when the popup is shut,
   * but chrome.alarms clamps sub-minute periods, so relying on it alone leaves
   * an approved pairing unredeemed for up to a minute while the user stares at
   * a popup that says it is not connected.
   */
  | { type: 'PAIRING_POLL' }
  | { type: 'PAIRING_CANCEL' }
  | { type: 'GROUPS_LIST' }
  | { type: 'SETTINGS_SET_GROUP'; groupId: string }
  | { type: 'ENTRIES_LIST'; groupId: string; query?: string }
  /**
   * Autofill seam, shipped and tested in v1 though no v1 screen calls it: a
   * pure filter over the cached metadata. No API call, therefore no audit
   * event, which is what makes autofill compatible with the vault's audit log.
   */
  | { type: 'ENTRIES_MATCH'; pageUrl: string }
  /**
   * Takes an id, never a value. The secret goes API → service worker →
   * offscreen document and never enters the popup's Vue tree, so it cannot be
   * retained in a reactive ref or captured in a devtools snapshot.
   */
  | { type: 'CLIPBOARD_COPY'; entryId: string; field: 'login' | 'password' }

/** Maps each request to the payload its handler resolves with. */
export interface ResponsePayloads {
  CONNECTION_GET_STATE: ConnectionState
  CONNECTION_SET_VAULT_URL: ConnectionState
  CONNECTION_DISCONNECT: ConnectionState
  PAIRING_START: { userCode: string; expiresAt: string; pollIntervalSeconds: number }
  PAIRING_POLL: ConnectionState
  PAIRING_CANCEL: ConnectionState
  GROUPS_LIST: GroupSummary[]
  SETTINGS_SET_GROUP: ConnectionState
  ENTRIES_LIST: { entries: EntrySummary[]; hiddenCount: number }
  ENTRIES_MATCH: EntrySummary[]
  CLIPBOARD_COPY: { clearsInSeconds: number | null }
}

export type RequestType = Request['type']
export type PayloadFor<T extends RequestType> = ResponsePayloads[T]
export type ResponseFor<T extends RequestType> = Result<PayloadFor<T>>

/** Service worker → popup pushes. The popup re-renders; it never polls. */
export type PushEvent =
  | { type: 'EVENT'; event: 'AUTH_LOST'; reason: 'expired' | 'revoked' }
  | { type: 'EVENT'; event: 'LOCKED' }
  | { type: 'EVENT'; event: 'CONNECTION_CHANGED' }
  | { type: 'EVENT'; event: 'CLIPBOARD_CLEARED' }

/** Service worker → offscreen document. Separate channel, carries the secret. */
export type OffscreenRequest =
  | { type: 'OFFSCREEN_COPY'; value: string; clearAfterSeconds: number | null }
  | { type: 'OFFSCREEN_CLEAR' }
