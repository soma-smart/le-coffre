import { InvalidServiceAccountNameError } from './errors'

/**
 * A machine identity owned by a group, used to reach that group's secrets from
 * an automation rather than from a person.
 *
 * `token` only ever exists on the object returned by creation or rotation: the
 * backend stores its hash and can never show it again.
 */
export interface ServiceAccount {
  id: string
  groupId: string
  name: string
  /**
   * Creator and creation date come from the account's creation event rather
   * than from its row, so an account whose event is missing still lists — with
   * these left empty.
   */
  createdByUserId: string | null
  createdByUserName: string | null
  createdAt: string | null
  revokedAt: string | null
}

export interface CreatedServiceAccount {
  id: string
  groupId: string
  name: string
  token: string
}

export interface RotatedServiceAccountToken {
  id: string
  token: string
}

/**
 * Every service account of one group, revoked ones included, plus how much of
 * the group's budget they use.
 *
 * Revoked accounts are kept indefinitely for the audit trail, so the list is
 * not a list of usable credentials — `active` is.
 */
export interface ServiceAccountPage {
  accounts: ServiceAccount[]
  /** Accounts that can still authenticate right now. */
  active: number
  /** How many may be active at once in one group, enforced by the server. */
  maxActive: number
}

export type ServiceAccountStatus = 'active' | 'revoked'

/** The server rejects a longer name with a 400. */
export const SERVICE_ACCOUNT_NAME_MAX_LENGTH = 100

/**
 * Reads the lifecycle state of an account. Unlike a one-time link, nothing
 * expires here: an account is usable until somebody revokes it.
 */
export function statusOf(account: ServiceAccount): ServiceAccountStatus {
  return account.revokedAt ? 'revoked' : 'active'
}

/** Only an active account can still be rotated or revoked. */
export function isActive(account: ServiceAccount): boolean {
  return statusOf(account) === 'active'
}

/** PrimeVue Tag severity for an account's lifecycle state. */
export function severityForStatus(status: ServiceAccountStatus): 'success' | 'secondary' {
  return status === 'active' ? 'success' : 'secondary'
}

export function activeAccounts(page: ServiceAccountPage): ServiceAccount[] {
  return page.accounts.filter(isActive)
}

export function revokedAccounts(page: ServiceAccountPage): ServiceAccount[] {
  return page.accounts.filter((account) => !isActive(account))
}

/**
 * Whether another account may be created.
 *
 * Read from the server's own counters rather than by counting the returned
 * accounts: the counters are what the server enforces the cap against, so
 * deriving the answer from the array would risk inviting a creation it then
 * refuses with a 409.
 */
export function canCreateAnotherServiceAccount(page: ServiceAccountPage): boolean {
  return page.active < page.maxActive
}

/**
 * Returns the name as the server will store it, or throws if it is unusable.
 *
 * Mirrors `ServiceAccount.validated_service_account_name` on the backend, down
 * to the trimming, so the UI refuses locally exactly what the API would refuse
 * with a 400.
 */
export function validateServiceAccountName(name: string): string {
  const stripped = name.trim()
  if (!stripped) {
    throw new InvalidServiceAccountNameError('Service account name cannot be blank')
  }
  if (stripped.length > SERVICE_ACCOUNT_NAME_MAX_LENGTH) {
    throw new InvalidServiceAccountNameError(
      `Service account name must be at most ${SERVICE_ACCOUNT_NAME_MAX_LENGTH} characters long`,
    )
  }
  return stripped
}
