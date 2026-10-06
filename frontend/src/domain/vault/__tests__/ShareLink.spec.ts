import { describe, expect, it } from 'vitest'
import { buildShareLinkUrl, readShareTokenFromFragment } from '@/domain/vault/ShareLink'

describe('share links', () => {
  it('puts the token in the fragment, never the path or query', () => {
    const url = new URL(buildShareLinkUrl('https://vault.example.com', 'abc_DEF-123'))
    expect(url.pathname).toBe('/vault-share')
    expect(url.search).toBe('')
    expect(url.hash).toBe('#abc_DEF-123')
  })

  it('reads back the exact token it encoded', () => {
    const token = 'BK5Zz4OJPJKwTdNlQD4Ba46oFHyldr_lhe62p2k0Kuk'
    const url = new URL(buildShareLinkUrl('https://vault.example.com', token))
    expect(readShareTokenFromFragment(url.hash)).toBe(token)
    expect(readShareTokenFromFragment('')).toBe('')
  })
})
