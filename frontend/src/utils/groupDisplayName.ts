/**
 * The backend names every personal group "{username}'s Personal Group" — a
 * fixed, English pattern baked straight into the stored name (see
 * user_creation_service.py on the server).
 */
const PERSONAL_GROUP_SUFFIX = "'s Personal Group"

/**
 * Whether a group name matches the backend's fixed personal-group pattern.
 * For callers that don't have a real `isPersonal` flag to hand (e.g. a group
 * name snapshotted onto an audit row, with no group record to ask), this is
 * the explicit way to derive one instead of leaving it to `translateGroupName`
 * to guess internally.
 */
export function isPersonalGroupName(name: string): boolean {
  return name.endsWith(PERSONAL_GROUP_SUFFIX)
}

/**
 * Rewrites a personal group's stored name into its translated display form.
 * Shared group names are free text chosen by their owners and must never be
 * touched, so `isPersonal` is trusted as given: pass `false` for anything
 * that isn't a personal group, `true` (or omit it) only for a name that is
 * actually in the backend's fixed pattern — use `isPersonalGroupName` first
 * if that isn't already known.
 */
export function translateGroupName(
  t: (key: string, params?: Record<string, unknown>) => string,
  name: string,
  isPersonal: boolean,
): string {
  if (isPersonal === false) return name

  const username = name.slice(0, -PERSONAL_GROUP_SUFFIX.length)
  return t('common.personalGroupName', { username })
}
