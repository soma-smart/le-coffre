import { describe, expect, it } from 'vitest'
import {
  isThresholdAtRisk,
  recoverableShareCount,
  wasOpenedSeveralTimes,
  type ShareLinkStatus,
  type ShareLinksOverview,
  type TrackedShareLink,
} from '@/domain/vault/ShareLinksOverview'

const link = (openCount: number): TrackedShareLink => ({
  shareIndex: 1,
  status: 'OPENED',
  expiresAt: null,
  firstOpenedAt: null,
  reopenableUntil: null,
  acknowledgedAt: null,
  openCount,
})

function overviewWith(
  threshold: number,
  counts: Partial<Record<ShareLinkStatus, number>>,
): ShareLinksOverview {
  return {
    setupId: 's',
    nbShares: 5,
    threshold,
    createdAt: null,
    links: [],
    counts: {
      PENDING: 0,
      OPENED: 0,
      OPENED_UNCONFIRMED: 0,
      ACKNOWLEDGED: 0,
      EXPIRED: 0,
      ...counts,
    },
  }
}

describe('ShareLinksOverview', () => {
  it('flags a link opened more than once, not one opened once or never', () => {
    expect(wasOpenedSeveralTimes(link(0))).toBe(false)
    expect(wasOpenedSeveralTimes(link(1))).toBe(false)
    expect(wasOpenedSeveralTimes(link(2))).toBe(true)
  })

  it('counts acknowledged, pending and opened shares as recoverable, the others as not', () => {
    const overview = overviewWith(3, {
      ACKNOWLEDGED: 1,
      PENDING: 2,
      OPENED: 1,
      OPENED_UNCONFIRMED: 4,
      EXPIRED: 8,
    })
    expect(recoverableShareCount(overview)).toBe(4)
  })

  it('is at risk only when recoverable shares fall below the threshold', () => {
    expect(isThresholdAtRisk(overviewWith(3, { ACKNOWLEDGED: 1, PENDING: 1, EXPIRED: 3 }))).toBe(
      true,
    )
    expect(isThresholdAtRisk(overviewWith(3, { ACKNOWLEDGED: 1, PENDING: 2, EXPIRED: 2 }))).toBe(
      false,
    )
    expect(isThresholdAtRisk(overviewWith(3, { ACKNOWLEDGED: 3, EXPIRED: 2 }))).toBe(false)
  })
})
