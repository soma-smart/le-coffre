/**
 * What every handler needs, passed explicitly rather than resolved from a
 * container. There is exactly one implementation of each, so a test just passes
 * a literal.
 */
import type { Browser } from '@/platform/browser'

export interface Clock {
  now(): Date
}

export interface Crypto {
  randomBytes(length: number): Uint8Array
  sha256(input: string): Promise<Uint8Array>
}

export interface Deps {
  browser: Browser
  clock: Clock
  crypto: Crypto
  /** Injected so tests can drive the client without a network. */
  makeClient: (vaultUrl: string, token: string | null) => VaultClientLike
}

/** The slice of VaultClient the handlers actually use. */
export interface VaultClientLike {
  health(): Promise<import('@/domain/errors').Result<{ status: string }>>
  vaultStatus(): Promise<import('@/domain/errors').Result<{ status: string }>>
  startPairing(
    codeChallenge: string,
    deviceName: string,
  ): Promise<import('@/domain/errors').Result<import('@/api/schemas').StartPairingDto>>
  exchangePairing(
    userCode: string,
    codeVerifier: string,
  ): Promise<import('@/domain/errors').Result<import('@/api/schemas').ExchangePairingDto>>
  session(): Promise<import('@/domain/errors').Result<import('@/api/schemas').ExtensionSessionDto>>
  listGroups(): Promise<import('@/domain/errors').Result<import('@/domain/group').Group[]>>
  listEntries(): Promise<import('@/domain/errors').Result<import('@/domain/entry').Entry[]>>
  revealPassword(entryId: string): Promise<import('@/domain/errors').Result<string>>
}
