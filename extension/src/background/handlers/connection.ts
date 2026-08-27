/**
 * First run and teardown: storing the vault URL, reporting where the user is in
 * the flow, and disconnecting.
 */
import { err, ok, type Result } from '@/domain/errors'
import { normalizeVaultUrl, toApiMatchPattern } from '@/domain/vaultUrl'
import type { ConnectionState } from '@/shared/messages'
import { LOCAL_KEYS } from '@/shared/storageKeys'

import type { Deps } from '../deps'
import {
  clearEverything,
  readMatchPattern,
  readPairing,
  readSelectedGroupId,
  readToken,
  readVaultUrl,
} from '../session'

/**
 * Where the popup should send the user next.
 *
 * Checks the host permission before the token, because a revoked permission
 * makes every request fail with a bare "Failed to fetch" that is
 * indistinguishable from the server being down.
 */
export async function getConnectionState(deps: Deps): Promise<Result<ConnectionState>> {
  const vaultUrl = await readVaultUrl(deps.browser)
  if (!vaultUrl) return ok({ status: 'unconfigured' })

  const pattern = await readMatchPattern(deps.browser)
  if (!pattern || !(await deps.browser.permissions.contains([pattern]))) {
    return ok({ status: 'permission-missing', vaultUrl })
  }

  const token = await readToken(deps.browser, deps.clock.now())
  if (!token) {
    // A pairing already in flight is its own state, distinct from "never
    // paired". Collapsing the two is what made the popup restart pairing,
    // and open a second tab, every time it was reopened while the user was
    // still approving, overwriting the verifier the approved request needed.
    const pairing = await readPairing(deps.browser)
    if (pairing && new Date(pairing.expiresAt).getTime() > deps.clock.now().getTime()) {
      return ok({
        status: 'pairing',
        vaultUrl,
        userCode: pairing.userCode,
        expiresAt: pairing.expiresAt,
      })
    }
    return ok({ status: 'unpaired', vaultUrl })
  }

  const session = await deps.makeClient(vaultUrl, token).session()
  if (!session.ok) {
    if (session.error.kind === 'AUTH_LOST') return ok({ status: 'unpaired', vaultUrl })
    if (session.error.kind === 'VAULT_LOCKED') return ok({ status: 'locked', vaultUrl })
    return err(session.error)
  }

  return ok({
    status: 'ready',
    vaultUrl,
    email: session.data.email,
    displayName: session.data.display_name,
    groupId: await readSelectedGroupId(deps.browser),
  })
}

/**
 * Store a vault URL after checking something Le Coffre-shaped answers there.
 *
 * The host permission must already have been granted: `permissions.request()`
 * has to run inside a user gesture, which only the popup has.
 */
export async function setVaultUrl(deps: Deps, rawUrl: string): Promise<Result<ConnectionState>> {
  const vaultUrl = normalizeVaultUrl(rawUrl)
  const pattern = vaultUrl ? toApiMatchPattern(vaultUrl) : null
  if (!vaultUrl || !pattern) {
    return err({ kind: 'NOT_A_VAULT' })
  }

  if (!(await deps.browser.permissions.contains([pattern]))) {
    return err({ kind: 'PERMISSION_MISSING', origin: vaultUrl })
  }

  const client = deps.makeClient(vaultUrl, null)

  const health = await client.health()
  if (!health.ok) return err(health.error)

  // A locked vault is still a vault: store the URL so the popup can show the
  // locked state rather than sending the user back to the first screen.
  const status = await client.vaultStatus()
  if (!status.ok && status.error.kind !== 'VAULT_LOCKED') return err(status.error)

  await deps.browser.local.set(LOCAL_KEYS.vaultUrl, vaultUrl)
  await deps.browser.local.set(LOCAL_KEYS.apiMatchPattern, pattern)

  return getConnectionState(deps)
}

/** Forget everything, including the host permission. */
export async function disconnect(deps: Deps): Promise<Result<ConnectionState>> {
  const pattern = await readMatchPattern(deps.browser)
  if (pattern) {
    await deps.browser.permissions.remove([pattern])
  }
  await clearEverything(deps.browser)
  return ok({ status: 'unconfigured' })
}
