import { describe, expect, it } from 'vitest'

import { parseWebUrl, toSafeWebUrl } from '../webUrl'

describe('toSafeWebUrl', () => {
  it.each(['https://github.com/login', 'http://intranet.example:8080/app'])(
    'accepts %s',
    (fine) => {
      expect(toSafeWebUrl(fine)).toBe(fine)
    },
  )

  it('canonicalises what it accepts', () => {
    expect(toSafeWebUrl('  HTTPS://GitHub.com  ')).toBe('https://github.com/')
  })

  it.each([
    'javascript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'file:///etc/passwd',
    'chrome://settings',
    'chrome-extension://abc/popup.html',
  ])('refuses %s', (hostile) => {
    // A vault entry's url is typed by whoever created the entry, and it ends
    // up in tabs.create. Anything but http(s) is a navigation primitive.
    expect(toSafeWebUrl(hostile)).toBeNull()
    expect(parseWebUrl(hostile)).toBeNull()
  })

  it.each(['/login', 'github.com', 'login/page', 'not a url'])(
    'refuses a relative or scheme-less value: %s',
    (relative) => {
      // Nothing safe to resolve it against.
      expect(toSafeWebUrl(relative)).toBeNull()
    },
  )

  it.each(['', '   ', null, undefined])('refuses empty input %s', (empty) => {
    expect(toSafeWebUrl(empty)).toBeNull()
  })
})
