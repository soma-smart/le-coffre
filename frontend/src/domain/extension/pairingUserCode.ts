/**
 * The pairing code the user reads off their extension and types into the
 * approval page: two groups of four, uppercase letters and digits, joined by a
 * dash (`K7QM-3XR9`).
 *
 * Typed, not linked. The page used to take the code from the URL fragment and
 * ask the user to check it against the extension, which let whoever wrote the
 * link supply the reference value: register a pairing, send the victim a link
 * on the real vault domain, and the victim approves the attacker's extension.
 * A code the user has to copy from their own popup cannot be planted.
 */
export const PAIRING_USER_CODE_PATTERN = /^[A-Z0-9]{4}-[A-Z0-9]{4}$/

/**
 * Normalise what a human typed into the canonical form, or null when it is not
 * a code at all. Case, whitespace and a missing or misplaced dash are not
 * signal; the backend applies the same tolerance.
 */
export function normalizePairingUserCode(input: string): string | null {
  const compact = input.toUpperCase().replace(/[\s-]/g, '')
  if (compact.length !== 8) return null
  const candidate = `${compact.slice(0, 4)}-${compact.slice(4)}`
  return PAIRING_USER_CODE_PATTERN.test(candidate) ? candidate : null
}
