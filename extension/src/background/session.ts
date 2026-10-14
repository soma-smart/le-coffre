/**
 * Connection and credential state, read from storage on every call.
 *
 * Stateless on purpose: MV3 terminates the service worker after ~30s idle and
 * restarts it on the next event, so anything cached in a module-level variable
 * silently evaporates.
 */
import type { Browser } from '@/platform/browser'
import { ALARMS, LOCAL_KEYS, SESSION_KEYS } from '@/shared/storageKeys'

export interface StoredSettings {
  clipboardClearSeconds: number
  idleSweepMinutes: number
}

export const DEFAULT_SETTINGS: StoredSettings = {
  clipboardClearSeconds: 30,
  idleSweepMinutes: 15,
}

/** What the idle sweep needs to know about the last clipboard write. */
export interface ClipboardWrite {
  /** When the offscreen document clears it by itself; null when it never will. */
  clearsAt: string | null
}

export interface PairingInProgress {
  userCode: string
  verifier: string
  expiresAt: string
  pollIntervalSeconds: number
}

export async function readVaultUrl(browser: Browser): Promise<string | null> {
  return (await browser.local.get<string>(LOCAL_KEYS.vaultUrl)) ?? null
}

export async function readMatchPattern(browser: Browser): Promise<string | null> {
  return (await browser.local.get<string>(LOCAL_KEYS.apiMatchPattern)) ?? null
}

export async function readSettings(browser: Browser): Promise<StoredSettings> {
  const stored = await browser.local.get<Partial<StoredSettings>>(LOCAL_KEYS.settings)
  return { ...DEFAULT_SETTINGS, ...(stored ?? {}) }
}

export async function readSelectedGroupId(browser: Browser): Promise<string | null> {
  return (await browser.local.get<string>(LOCAL_KEYS.selectedGroupId)) ?? null
}

/**
 * The bearer token, or null once it has expired.
 *
 * Expiry is checked here rather than left to the server so the popup can show
 * "reconnect" instead of a failed request.
 */
export async function readToken(browser: Browser, now: Date): Promise<string | null> {
  const token = await browser.local.get<string>(LOCAL_KEYS.token)
  if (!token) return null

  const expiresAt = await browser.local.get<string>(LOCAL_KEYS.tokenExpiresAt)
  if (expiresAt && new Date(expiresAt).getTime() <= now.getTime()) return null

  return token
}

export async function storeToken(
  browser: Browser,
  token: string,
  expiresAt: string,
): Promise<void> {
  await browser.local.set(LOCAL_KEYS.token, token)
  await browser.local.set(LOCAL_KEYS.tokenExpiresAt, expiresAt)
}

/**
 * Drop the credential and everything derived from it, keeping configuration.
 *
 * Used by a 401, by losing the host permission, and by a change of vault
 * address. Not by the idle sweep, which keeps the token on purpose. The vault
 * URL survives so the user reconnects rather than reconfigures.
 */
export async function clearCredentials(browser: Browser): Promise<void> {
  await browser.local.remove(LOCAL_KEYS.token)
  await browser.local.remove(LOCAL_KEYS.tokenExpiresAt)
  await browser.session.clear()
  // No credential, nothing left for the idle sweep to guard.
  await browser.alarms.clear(ALARMS.idleSweep)
}

/** Wipe everything, including configuration. Used by Disconnect. */
export async function clearEverything(browser: Browser): Promise<void> {
  await browser.local.clear()
  await browser.session.clear()
  await browser.alarms.clear(ALARMS.idleSweep)
}

export async function readPairing(browser: Browser): Promise<PairingInProgress | null> {
  return (await browser.session.get<PairingInProgress>(SESSION_KEYS.pairing)) ?? null
}

export async function storePairing(browser: Browser, pairing: PairingInProgress): Promise<void> {
  await browser.session.set(SESSION_KEYS.pairing, pairing)
}

export async function clearPairing(browser: Browser): Promise<void> {
  await browser.session.remove(SESSION_KEYS.pairing)
}

export async function stampActivity(browser: Browser, now: Date): Promise<void> {
  await browser.session.set(SESSION_KEYS.lastActivityAt, now.toISOString())
}

/** True when the idle window has elapsed since the last authenticated call. */
export async function isIdleExpired(
  browser: Browser,
  now: Date,
  idleSweepMinutes: number,
): Promise<boolean> {
  const last = await browser.session.get<string>(SESSION_KEYS.lastActivityAt)
  if (!last) return false
  return now.getTime() - new Date(last).getTime() >= idleSweepMinutes * 60_000
}

export async function recordClipboardWrite(browser: Browser, write: ClipboardWrite): Promise<void> {
  await browser.session.set(SESSION_KEYS.clipboardWrite, write)
}

export async function readClipboardWrite(browser: Browser): Promise<ClipboardWrite | null> {
  return (await browser.session.get<ClipboardWrite>(SESSION_KEYS.clipboardWrite)) ?? null
}
