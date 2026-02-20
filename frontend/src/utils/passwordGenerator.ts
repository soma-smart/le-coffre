export interface PasswordGeneratorOptions {
  length: number
  includeUppercase: boolean
  includeLowercase: boolean
  includeNumbers: boolean
  includeSymbols: boolean
}

const DEFAULT_OPTIONS: PasswordGeneratorOptions = {
  length: 16,
  includeUppercase: true,
  includeLowercase: true,
  includeNumbers: true,
  includeSymbols: true,
}

const UPPERCASE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const LOWERCASE = 'abcdefghijklmnopqrstuvwxyz'
const NUMBERS = '0123456789'
const SYMBOLS = '!@#$%^&*()_+-=[]{}|;:,.<>?'

/**
 * Generate a cryptographically secure random password
 * @param options - Password generation options
 * @returns Generated password string
 */
export function generatePassword(options: Partial<PasswordGeneratorOptions> = {}): string {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // Validate that at least one character type is selected
  if (
    !opts.includeUppercase &&
    !opts.includeLowercase &&
    !opts.includeNumbers &&
    !opts.includeSymbols
  ) {
    throw new Error('At least one character type must be selected')
  }

  // Validate length
  if (opts.length < 4 || opts.length > 128) {
    throw new Error('Password length must be between 4 and 128 characters')
  }

  // Build character set
  let charset = ''
  const requiredChars: string[] = []

  if (opts.includeUppercase) {
    charset += UPPERCASE
    requiredChars.push(getRandomChar(UPPERCASE))
  }
  if (opts.includeLowercase) {
    charset += LOWERCASE
    requiredChars.push(getRandomChar(LOWERCASE))
  }
  if (opts.includeNumbers) {
    charset += NUMBERS
    requiredChars.push(getRandomChar(NUMBERS))
  }
  if (opts.includeSymbols) {
    charset += SYMBOLS
    requiredChars.push(getRandomChar(SYMBOLS))
  }

  // Generate password ensuring at least one character from each selected type
  const remainingLength = opts.length - requiredChars.length
  const randomChars: string[] = []

  for (let i = 0; i < remainingLength; i++) {
    randomChars.push(getRandomChar(charset))
  }

  // Combine required and random characters, then shuffle
  const allChars = [...requiredChars, ...randomChars]
  return shuffleArray(allChars).join('')
}

/**
 * Get a cryptographically secure random character from a charset
 */
function getRandomChar(charset: string): string {
  const randomIndex = getSecureRandomInt(0, charset.length)
  return charset[randomIndex]
}

/**
 * Generate a cryptographically secure random integer between min (inclusive) and max (exclusive)
 */
function getSecureRandomInt(min: number, max: number): number {
  const range = max - min
  const bytesNeeded = Math.ceil(Math.log2(range) / 8)
  const maxValue = Math.pow(256, bytesNeeded)
  const threshold = maxValue - (maxValue % range)

  let randomValue: number
  const randomBytes = new Uint8Array(bytesNeeded)

  do {
    crypto.getRandomValues(randomBytes)
    randomValue = 0
    for (let i = 0; i < bytesNeeded; i++) {
      randomValue = randomValue * 256 + randomBytes[i]
    }
  } while (randomValue >= threshold)

  return min + (randomValue % range)
}

/**
 * Shuffle an array using Fisher-Yates algorithm with cryptographically secure randomness
 */
function shuffleArray<T>(array: T[]): T[] {
  const result = [...array]
  for (let i = result.length - 1; i > 0; i--) {
    const j = getSecureRandomInt(0, i + 1)
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}

/**
 * Estimate password strength based on entropy
 * @param password - The password to evaluate
 * @returns Strength category: 'weak', 'fair', 'good', 'strong', 'very-strong'
 */
export function estimatePasswordStrength(password: string): {
  strength: 'weak' | 'fair' | 'good' | 'strong' | 'very-strong'
  entropy: number
} {
  let charset = 0

  if (/[a-z]/.test(password)) charset += 26
  if (/[A-Z]/.test(password)) charset += 26
  if (/[0-9]/.test(password)) charset += 10
  if (/[^a-zA-Z0-9]/.test(password)) charset += 32

  const entropy = password.length * Math.log2(charset)

  let strength: 'weak' | 'fair' | 'good' | 'strong' | 'very-strong'
  if (entropy < 40) strength = 'weak'
  else if (entropy < 60) strength = 'fair'
  else if (entropy < 80) strength = 'good'
  else if (entropy < 100) strength = 'strong'
  else strength = 'very-strong'

  return { strength, entropy }
}
