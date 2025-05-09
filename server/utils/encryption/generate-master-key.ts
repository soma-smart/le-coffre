import crypto from 'node:crypto'
import { split } from 'shamir-secret-sharing'

/**
 * Generates a cryptographically secure random master key.
 *
 * @returns {Promise<Uint8Array>} A promise that resolves to a 32-byte Uint8Array containing the generated master key.
 */
export function generateMasterKey(): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(32))
}

/**
 * Splits a master key into multiple shares using a secret sharing scheme.
 *
 * @param masterKey - The master key to be split, represented as a Uint8Array.
 * @param sharesNumber - The total number of shares to generate.
 * @param threshold - The minimum number of shares required to reconstruct the master key.
 * @returns A promise that resolves to an array of shares, each represented as a hexadecimal string.
 *
 * @remarks
 * This function uses a secret sharing algorithm to split the master key into
 * the specified number of shares. Each share is converted from a Uint8Array
 * to a hexadecimal string for easier storage and transmission.
 *
 * @example
 * ```typescript
 * const masterKey = new Uint8Array([1, 2, 3, 4, 5]);
 * const sharesNumber = 5;
 * const threshold = 3;
 * const shares = await getSplitShares(masterKey, sharesNumber, threshold);
 * console.log(shares); // ['hexShare1', 'hexShare2', ...]
 * ```
 */
export async function getSplitShares(
  masterKey: Uint8Array,
  sharesNumber: number,
  threshold: number,
): Promise<string[]> {
  const shares = await split(
    masterKey,
    sharesNumber,
    threshold,
  )
  // convert the shares from Uint8Array to hex
  const hexShares = shares.map(share =>
    Array.from(share)
      .map(b => b.toString(16).padStart(2, '0'))
      .join(''),
  )

  return hexShares
}
