import { describe, expect, it } from 'vitest'
import {
  clampThresholdToShares,
  isValidShamirConfig,
  SHAMIR_MAX_SHARES,
  SHAMIR_MIN_SHARES,
} from '@/domain/vault/ShamirConfig'

describe('isValidShamirConfig', () => {
  it('accepts the minimum valid config', () => {
    expect(isValidShamirConfig({ shares: SHAMIR_MIN_SHARES, threshold: SHAMIR_MIN_SHARES })).toBe(
      true,
    )
  })

  it('accepts the maximum valid config', () => {
    expect(isValidShamirConfig({ shares: SHAMIR_MAX_SHARES, threshold: SHAMIR_MAX_SHARES })).toBe(
      true,
    )
  })

  it('accepts a typical 3-of-5 setup', () => {
    expect(isValidShamirConfig({ shares: 5, threshold: 3 })).toBe(true)
  })

  it('rejects shares below the minimum', () => {
    expect(isValidShamirConfig({ shares: SHAMIR_MIN_SHARES - 1, threshold: 2 })).toBe(false)
  })

  it('rejects shares above the maximum', () => {
    expect(isValidShamirConfig({ shares: SHAMIR_MAX_SHARES + 1, threshold: 3 })).toBe(false)
  })

  it('rejects threshold below the minimum', () => {
    expect(isValidShamirConfig({ shares: 5, threshold: SHAMIR_MIN_SHARES - 1 })).toBe(false)
  })

  it('rejects threshold greater than shares', () => {
    expect(isValidShamirConfig({ shares: 3, threshold: 5 })).toBe(false)
  })

  it('rejects non-integer values', () => {
    expect(isValidShamirConfig({ shares: 3.5, threshold: 2 })).toBe(false)
    expect(isValidShamirConfig({ shares: 5, threshold: 2.5 })).toBe(false)
  })
})

describe('clampThresholdToShares', () => {
  it('leaves a valid config untouched', () => {
    expect(clampThresholdToShares({ shares: 5, threshold: 3 })).toEqual({ shares: 5, threshold: 3 })
  })

  it('clamps threshold down to shares when it overshoots', () => {
    expect(clampThresholdToShares({ shares: 3, threshold: 5 })).toEqual({ shares: 3, threshold: 3 })
  })

  it('is a no-op when threshold equals shares', () => {
    expect(clampThresholdToShares({ shares: 4, threshold: 4 })).toEqual({ shares: 4, threshold: 4 })
  })
})
