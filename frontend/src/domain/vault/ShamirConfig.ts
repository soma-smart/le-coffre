/**
 * Shamir Secret Sharing configuration invariants.
 *
 * A valid config satisfies: SHAMIR_MIN_SHARES ≤ threshold ≤ shares ≤ SHAMIR_MAX_SHARES.
 * Keeping the bounds and the validator in the domain means any UI, use case, or
 * router guard that needs to check SSS config asks the same source of truth,
 * and the constants are discoverable alongside the vault entity.
 */

export const SHAMIR_MIN_SHARES = 2
export const SHAMIR_MAX_SHARES = 16

export interface ShamirConfig {
  shares: number
  threshold: number
}

export function isValidShamirConfig(config: ShamirConfig): boolean {
  const { shares, threshold } = config
  return (
    Number.isInteger(shares) &&
    Number.isInteger(threshold) &&
    shares >= SHAMIR_MIN_SHARES &&
    shares <= SHAMIR_MAX_SHARES &&
    threshold >= SHAMIR_MIN_SHARES &&
    threshold <= shares
  )
}

/**
 * If `threshold > shares`, return a new config with threshold clamped down to
 * match. Used by the setup form's watchers so the invariant holds live as the
 * user tweaks either spinner.
 */
export function clampThresholdToShares(config: ShamirConfig): ShamirConfig {
  if (config.threshold > config.shares) {
    return { shares: config.shares, threshold: config.shares }
  }
  return config
}
