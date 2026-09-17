/**
 * The backend names every personal group "{username}'s Personal Group" — a
 * fixed, English pattern baked straight into the stored name (see
 * user_creation_service.py on the server). Shared group names are free text
 * chosen by their owners and must never be touched; this rewrites only that
 * one fixed suffix, and only when it actually matches, so a group that
 * merely happens to be named that way, or a future backend naming change,
 * both degrade to showing the raw name unchanged.
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

export function translateGroupName(
  t: (key: string, params?: Record<string, unknown>) => string,
  name: string,
  isPersonal?: boolean,
): string {
  if (isPersonal === false || !isPersonalGroupName(name)) return name

  const username = name.slice(0, -PERSONAL_GROUP_SUFFIX.length)
  return t('common.personalGroupName', { username })
}
