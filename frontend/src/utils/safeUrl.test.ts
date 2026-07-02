import { describe, expect, it } from 'vitest'

import { isSafeHttpUrl, normalizeExternalHttpUrl } from './safeUrl'

describe('safeUrl', () => {
  it.each(['https://example.com', 'http://example.com/path?q=1', ' HTTPS://example.com '])(
    'accepts %s',
    (url) => {
      expect(isSafeHttpUrl(url)).toBe(true)
      expect(normalizeExternalHttpUrl(url)).toMatch(/^https?:\/\//i)
    },
  )

  it.each([
    'javascript:alert(1)',
    'data:text/html,<script></script>',
    '//example.com',
    '/local',
    'ftp://example.com',
  ])('rejects %s', (url) => {
    expect(isSafeHttpUrl(url)).toBe(false)
    expect(normalizeExternalHttpUrl(url)).toBeNull()
  })
})
