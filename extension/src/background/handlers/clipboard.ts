/**
 * Copying a value to the clipboard, without it ever reaching the popup.
 *
 * The handler takes an entry id, fetches the secret itself, and hands it to the
 * offscreen document. The popup only learns how long until the clipboard is
 * cleared, so the secret cannot be retained in a reactive ref or captured in a
 * devtools snapshot of the Vue tree.
 */
import { err, ok, type Result } from '@/domain/errors'
import { SESSION_KEYS } from '@/shared/storageKeys'

import type { Deps } from '../deps'
import { readSettings } from '../session'
import { revealSecret } from './vault'

export interface ClipboardResult {
  clearsInSeconds: number | null
}

/**
 * Copy a login or a password.
 *
 * A login comes from the cached metadata and costs nothing. A password is
 * fetched on demand, because every fetch writes a PasswordAccessedEvent in the
 * vault's audit log: prefetching would flood it and make the audit screen
 * useless.
 */
export async function copyToClipboard(
  deps: Deps,
  entryId: string,
  field: 'login' | 'password',
): Promise<Result<ClipboardResult>> {
  const settings = await readSettings(deps.browser)
  const clearAfterSeconds =
    settings.clipboardClearSeconds > 0 ? settings.clipboardClearSeconds : null

  let value: string

  if (field === 'password') {
    const revealed = await revealSecret(deps, entryId)
    if (!revealed.ok) return revealed
    value = revealed.data
  } else {
    const cached = await deps.browser.session.get<{
      entries: Array<{ id: string; login: string | null }>
    }>(SESSION_KEYS.entriesCache)
    const entry = cached?.entries.find((candidate) => candidate.id === entryId)
    if (!entry?.login) return err({ kind: 'NOT_FOUND' })
    value = entry.login
  }

  const copied = await deps.browser.clipboard.copy(value, clearAfterSeconds)
  if (!copied) {
    // Deliberately NOT returning the value for the popup to copy instead. That
    // fallback would put a live secret in the Vue tree, which is the one thing
    // this whole path exists to avoid. A failed copy the user can retry is a
    // better trade than a weaker invariant.
    return err({ kind: 'CLIPBOARD_UNAVAILABLE' })
  }

  return ok({ clearsInSeconds: clearAfterSeconds })
}
