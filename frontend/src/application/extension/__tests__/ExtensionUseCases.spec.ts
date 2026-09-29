import { describe, expect, it, vi } from 'vitest'
import { ApprovePairingUseCase } from '@/application/extension/ApprovePairing'
import { DenyPairingUseCase } from '@/application/extension/DenyPairing'
import { DisconnectAllExtensionsUseCase } from '@/application/extension/DisconnectAllExtensions'
import { DisconnectExtensionUseCase } from '@/application/extension/DisconnectExtension'
import { GetPairingUseCase } from '@/application/extension/GetPairing'
import { ListConnectedExtensionsUseCase } from '@/application/extension/ListConnectedExtensions'
import type { ConnectedExtension } from '@/domain/extension/Extension'
import {
  ExtensionPairingUnavailableError,
  InvalidPairingUserCodeError,
} from '@/domain/extension/errors'
import { InMemoryExtensionGateway } from '@/infrastructure/in_memory/InMemoryExtensionGateway'

const NOW = new Date('2026-08-27T12:00:00Z')

function pairing(overrides: Partial<Parameters<InMemoryExtensionGateway['seedPairing']>[0]> = {}) {
  return {
    userCode: 'K7QM-3XR9',
    deviceName: 'Chrome on macOS',
    createdAt: NOW,
    expiresAt: new Date(NOW.getTime() + 300_000),
    accessLifetimeSeconds: 30 * 86400,
    createdFromIp: '203.0.113.5',
    isResolved: false,
    ...overrides,
  }
}

function connected(overrides: Partial<ConnectedExtension> = {}): ConnectedExtension {
  return {
    id: 'ext-1',
    deviceName: 'Chrome on macOS',
    createdAt: NOW,
    expiresAt: new Date(NOW.getTime() + 30 * 86_400_000),
    lastUsedAt: null,
    revokedAt: null,
    createdFromIp: '203.0.113.5',
    isActive: true,
    ...overrides,
  }
}

describe('GetPairingUseCase', () => {
  it('should return the pairing when the code is known', async () => {
    const gateway = new InMemoryExtensionGateway().seedPairing(pairing())

    const result = await new GetPairingUseCase(gateway).execute({ userCode: 'K7QM-3XR9' })

    expect(result.deviceName).toBe('Chrome on macOS')
    expect(result.createdFromIp).toBe('203.0.113.5')
  })

  it('should throw when the code is unknown', async () => {
    const gateway = new InMemoryExtensionGateway()

    await expect(
      new GetPairingUseCase(gateway).execute({ userCode: 'ZZZZ-ZZZZ' }),
    ).rejects.toBeInstanceOf(ExtensionPairingUnavailableError)
  })

  it.each(['k7qm3xr9', ' K7QM 3XR9 ', 'k7qm-3xr9', 'K7QM3XR-9'])(
    'should normalise %j to what the extension displays',
    async (typed) => {
      // The code is read off a popup and typed by hand: case, whitespace and
      // the dash are not signal, and the backend is equally tolerant.
      const gateway = new InMemoryExtensionGateway().seedPairing(pairing())

      const result = await new GetPairingUseCase(gateway).execute({ userCode: typed })

      expect(result.userCode).toBe('K7QM-3XR9')
    },
  )

  it.each(['', 'K7QM', 'K7QM-3XR9-1', 'K7QM_3XR9', 'K7QM-3XR!'])(
    'should refuse %j without asking the backend',
    async (typed) => {
      // The pairing routes are rate-limited per IP, and a malformed code can
      // only ever be a 400, so the use case stops it before the gateway.
      const gateway = new InMemoryExtensionGateway()
      const spy = vi.spyOn(gateway, 'getPairing')

      await expect(
        new GetPairingUseCase(gateway).execute({ userCode: typed }),
      ).rejects.toBeInstanceOf(InvalidPairingUserCodeError)
      expect(spy).not.toHaveBeenCalled()
    },
  )
})

describe('ApprovePairingUseCase', () => {
  it('should approve the pairing it was given', async () => {
    const gateway = new InMemoryExtensionGateway().seedPairing(pairing())

    await new ApprovePairingUseCase(gateway).execute({ userCode: 'K7QM-3XR9' })

    expect(gateway.approved).toEqual(['K7QM-3XR9'])
    expect(gateway.denied).toEqual([])
  })
})

describe('DenyPairingUseCase', () => {
  it('should deny the pairing it was given', async () => {
    const gateway = new InMemoryExtensionGateway().seedPairing(pairing())

    await new DenyPairingUseCase(gateway).execute({ userCode: 'K7QM-3XR9' })

    expect(gateway.denied).toEqual(['K7QM-3XR9'])
    expect(gateway.approved).toEqual([])
  })
})

describe('ListConnectedExtensionsUseCase', () => {
  it('should sort active extensions before disconnected ones', async () => {
    // Someone scanning this list is looking for what still has access.
    const gateway = new InMemoryExtensionGateway().seedExtensions([
      connected({ id: 'dead', isActive: false, createdAt: new Date(NOW.getTime() + 10_000) }),
      connected({ id: 'live', isActive: true, createdAt: NOW }),
    ])

    const result = await new ListConnectedExtensionsUseCase(gateway).execute()

    expect(result.map((extension) => extension.id)).toEqual(['live', 'dead'])
  })

  it('should sort the newest first within the same state', async () => {
    const gateway = new InMemoryExtensionGateway().seedExtensions([
      connected({ id: 'older', createdAt: new Date(NOW.getTime() - 10_000) }),
      connected({ id: 'newer', createdAt: NOW }),
    ])

    const result = await new ListConnectedExtensionsUseCase(gateway).execute()

    expect(result.map((extension) => extension.id)).toEqual(['newer', 'older'])
  })
})

describe('DisconnectExtensionUseCase', () => {
  it('should mark the extension inactive', async () => {
    const gateway = new InMemoryExtensionGateway().seedExtensions([connected()])

    await new DisconnectExtensionUseCase(gateway).execute({ extensionId: 'ext-1' })

    const remaining = await gateway.listConnectedExtensions()
    expect(remaining[0].isActive).toBe(false)
    expect(remaining[0].revokedAt).not.toBeNull()
  })
})

describe('DisconnectAllExtensionsUseCase', () => {
  it('should report how many were still active', async () => {
    const gateway = new InMemoryExtensionGateway().seedExtensions([
      connected({ id: 'a', isActive: true }),
      connected({ id: 'b', isActive: true }),
      connected({ id: 'c', isActive: false, revokedAt: NOW }),
    ])

    const revoked = await new DisconnectAllExtensionsUseCase(gateway).execute()

    expect(revoked).toBe(2)
  })

  it('should leave the original timestamp on an already disconnected extension', async () => {
    const earlier = new Date(NOW.getTime() - 86_400_000)
    const gateway = new InMemoryExtensionGateway().seedExtensions([
      connected({ id: 'c', isActive: false, revokedAt: earlier }),
    ])

    await new DisconnectAllExtensionsUseCase(gateway).execute()

    const remaining = await gateway.listConnectedExtensions()
    expect(remaining[0].revokedAt).toEqual(earlier)
  })
})
