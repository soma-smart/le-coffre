import { describe, expect, it } from 'vitest'
import { estimatePasswordStrength, generatePassword } from '@/utils/passwordGenerator'

describe('generatePassword', () => {
  it('respects the requested length', () => {
    expect(generatePassword({ length: 12 })).toHaveLength(12)
    expect(generatePassword({ length: 32 })).toHaveLength(32)
  })

  it('uses default length 16 when none is provided', () => {
    expect(generatePassword()).toHaveLength(16)
  })

  it('only emits characters from the selected charsets', () => {
    const onlyLower = generatePassword({
      length: 64,
      includeUppercase: false,
      includeLowercase: true,
      includeNumbers: false,
      includeSymbols: false,
    })
    expect(onlyLower).toMatch(/^[a-z]+$/)

    const onlyDigits = generatePassword({
      length: 64,
      includeUppercase: false,
      includeLowercase: false,
      includeNumbers: true,
      includeSymbols: false,
    })
    expect(onlyDigits).toMatch(/^[0-9]+$/)
  })

  it('guarantees at least one character from each selected charset', () => {
    // Run several iterations because randomness could mask a bug.
    for (let i = 0; i < 30; i++) {
      const pwd = generatePassword({
        length: 8,
        includeUppercase: true,
        includeLowercase: true,
        includeNumbers: true,
        includeSymbols: true,
      })
      expect(pwd).toMatch(/[A-Z]/)
      expect(pwd).toMatch(/[a-z]/)
      expect(pwd).toMatch(/[0-9]/)
      expect(pwd).toMatch(/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/)
    }
  })

  it('throws when no character type is selected', () => {
    expect(() =>
      generatePassword({
        includeUppercase: false,
        includeLowercase: false,
        includeNumbers: false,
        includeSymbols: false,
      }),
    ).toThrow(/at least one character type/i)
  })

  it('throws when length is below 4', () => {
    expect(() => generatePassword({ length: 3 })).toThrow(/length/i)
  })

  it('throws when length is above 128', () => {
    expect(() => generatePassword({ length: 129 })).toThrow(/length/i)
  })

  it('does not produce the same password twice in a row (statistical sanity)', () => {
    const a = generatePassword({ length: 32 })
    const b = generatePassword({ length: 32 })
    expect(a).not.toBe(b)
  })
})

describe('estimatePasswordStrength', () => {
  it('classifies a short single-charset password as weak', () => {
    const { strength, entropy } = estimatePasswordStrength('aaaa')
    expect(strength).toBe('weak')
    expect(entropy).toBeLessThan(40)
  })

  it('classifies a long mixed-charset password as very-strong', () => {
    const { strength, entropy } = estimatePasswordStrength('Aa1!Bb2@Cc3#Dd4$Ee5%Ff6^Gg7&Hh8*')
    expect(strength).toBe('very-strong')
    expect(entropy).toBeGreaterThanOrEqual(100)
  })

  it('returns each band at the documented entropy thresholds', () => {
    // 1 charset (lowercase only) → 26 symbols → log2(26) ≈ 4.7 per char.
    expect(estimatePasswordStrength('a'.repeat(8)).strength).toBe('weak') // ~37.6
    expect(estimatePasswordStrength('a'.repeat(10)).strength).toBe('fair') // ~47
    // 2 charsets (lower + upper) → 52 symbols → log2(52) ≈ 5.7
    expect(estimatePasswordStrength('aA'.repeat(7)).strength).toBe('good') // 14 chars * 5.7 ≈ 79.8
    // 3 charsets — mid-strong band (>= 80 but < 100).
    // 16 chars over 62 symbols (lower+upper+digits) → 16 * log2(62) ≈ 95.3
    expect(estimatePasswordStrength('aA1bC2dE3fG4hI5j').strength).toBe('strong')
  })
})
