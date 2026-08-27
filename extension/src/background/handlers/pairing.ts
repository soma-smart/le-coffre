/**
 * The pairing loop.
 *
 * Lives in the service worker rather than the popup because the popup is
 * destroyed on any outside click, and the user is about to click away to sign
 * in on the vault's website. A popup-owned poll would die exactly when it
 * matters.
 */
import { createPkcePair } from '@/domain/pkce'
import { err, ok, type Result } from '@/domain/errors'
import { toPairingApprovalLink } from '@/domain/vaultUrl'
import type { ConnectionState } from '@/shared/messages'
import { ALARMS, LOCAL_KEYS } from '@/shared/storageKeys'

import type { Deps } from '../deps'
import { clearPairing, readPairing, readVaultUrl, storePairing, storeToken } from '../session'
import { getConnectionState } from './connection'

const DEFAULT_DEVICE_NAME = 'Browser extension'

/**
 * Register a pairing, then open the approval page.
 *
 * Registering first is what makes the code a server-vouched fact: the approval
 * page can then show something the user matches against this popup, rather than
 * rendering text the caller supplied.
 */
export async function startPairing(
  deps: Deps,
): Promise<Result<{ userCode: string; expiresAt: string }>> {
  const vaultUrl = await readVaultUrl(deps.browser)
  if (!vaultUrl) return err({ kind: 'NOT_CONFIGURED' })

  const { verifier, challenge } = await createPkcePair(deps.crypto)
  const deviceName =
    (await deps.browser.local.get<string>(LOCAL_KEYS.deviceName)) ?? DEFAULT_DEVICE_NAME

  const started = await deps.makeClient(vaultUrl, null).startPairing(challenge, deviceName)
  if (!started.ok) return err(started.error)

  await storePairing(deps.browser, {
    userCode: started.data.user_code,
    verifier,
    expiresAt: started.data.expires_at,
    pollIntervalSeconds: started.data.poll_interval_seconds,
  })

  const approvalLink = toPairingApprovalLink(vaultUrl, started.data.user_code)
  if (approvalLink) {
    await deps.browser.tabs.create(approvalLink)
  }

  // chrome.alarms rather than setInterval: the worker is terminated on idle and
  // only an alarm wakes it back up.
  await deps.browser.alarms.schedule(
    ALARMS.pairingPoll,
    minutesFor(started.data.poll_interval_seconds),
  )

  return ok({ userCode: started.data.user_code, expiresAt: started.data.expires_at })
}

/**
 * chrome.alarms enforces a minimum period in release builds, so a 5-second poll
 * becomes the floor rather than the request. The popup polls faster while it is
 * open; this alarm is the safety net for when it is not.
 */
function minutesFor(seconds: number): number {
  return Math.max(seconds / 60, 0.5)
}

/**
 * One exchange attempt.
 *
 * Returns the connection state so the popup can simply re-render: `unpaired`
 * while pending, `ready` once redeemed.
 */
export async function pollPairing(deps: Deps): Promise<Result<ConnectionState>> {
  const pairing = await readPairing(deps.browser)
  if (!pairing) return getConnectionState(deps)

  const vaultUrl = await readVaultUrl(deps.browser)
  if (!vaultUrl) return err({ kind: 'NOT_CONFIGURED' })

  if (new Date(pairing.expiresAt).getTime() <= deps.clock.now().getTime()) {
    await cancelPairing(deps)
    return err({ kind: 'AUTH_LOST', reason: 'expired' })
  }

  const exchanged = await deps
    .makeClient(vaultUrl, null)
    .exchangePairing(pairing.userCode, pairing.verifier)

  if (!exchanged.ok) {
    // Denied, expired or already redeemed all arrive as the same generic 400,
    // which is what the server intends. Any of them ends this pairing.
    await cancelPairing(deps)
    return err(exchanged.error)
  }

  if (exchanged.data.status === 'pending' || !exchanged.data.token) {
    return getConnectionState(deps)
  }

  await storeToken(deps.browser, exchanged.data.token, exchanged.data.expires_at)
  await cancelPairing(deps)
  return getConnectionState(deps)
}

export async function cancelPairing(deps: Deps): Promise<Result<ConnectionState>> {
  await clearPairing(deps.browser)
  await deps.browser.alarms.clear(ALARMS.pairingPoll)
  return getConnectionState(deps)
}
