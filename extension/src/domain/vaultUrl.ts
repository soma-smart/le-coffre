/**
 * Everything about the user-supplied vault URL: validating it, deriving the
 * host permission to request, and building deep links back into the web app.
 *
 * Security-critical. The URL is typed by the user and later reaches both
 * `chrome.permissions.request()` and `chrome.tabs.create()`, so a bad value
 * here is either an over-broad grant or an arbitrary tab-open primitive.
 */
import { parseWebUrl } from './webUrl'

/**
 * True for a host that never leaves the machine: `localhost`, anything under
 * `.localhost`, the whole 127/8 block and the IPv6 loopback.
 *
 * `URL.hostname` keeps the brackets around an IPv6 literal, hence `[::1]`.
 */
export function isLoopbackHost(hostname: string): boolean {
  const host = hostname.toLowerCase()
  return (
    host === 'localhost' ||
    host.endsWith('.localhost') ||
    host === '[::1]' ||
    /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(host)
  )
}

function withProtocol(typed: string): string {
  return /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(typed) ? typed : `https://${typed}`
}

/**
 * Normalise a typed vault URL, or return null.
 *
 * Accepts a bare host and assumes https, since that is what people type.
 * Rejects every protocol but http and https: a `javascript:` or `data:` value
 * reaching `tabs.create` later would be a real hole.
 *
 * Plain http is accepted for loopback hosts only, which is where a developer
 * runs the vault. Anywhere else the bearer token and every password would
 * cross the network in the clear, and a warning the user can click through
 * is not a control: the address is refused, and `refusesPlainHttp` lets the
 * onboarding screen say why.
 *
 * Ported in spirit from frontend/src/utils/safeUrl.ts.
 */
export function normalizeVaultUrl(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  if (!trimmed) return null

  const url = parseWebUrl(withProtocol(trimmed))
  if (!url) return null
  if (url.protocol === 'http:' && !isLoopbackHost(url.hostname)) return null

  // Drop query and fragment, and strip a trailing slash from the path, so the
  // same vault typed three different ways yields one stored value and one
  // granted permission.
  const path = url.pathname.replace(/\/+$/, '')
  return `${url.origin}${path}`
}

/**
 * True when the typed value is refused for the one reason worth explaining:
 * plain http to a host that is not loopback. Every other refusal is "not a
 * vault address", which the onboarding screen says generically.
 */
export function refusesPlainHttp(value: string | null | undefined): boolean {
  const trimmed = value?.trim()
  if (!trimmed) return false

  const url = parseWebUrl(withProtocol(trimmed))
  return !!url && url.protocol === 'http:' && !isLoopbackHost(url.hostname)
}

/**
 * The narrowest host-permission pattern covering the API.
 *
 * `https://vault.example.com` becomes `https://vault.example.com/api/*`, not
 * `/*`: the extension never fetches anything outside `/api/`, and deep links go
 * through `chrome.tabs.create`, which needs no permission at all. Asking for
 * less is the difference between a prompt naming one path and one naming a
 * whole site.
 */
export function toApiMatchPattern(vaultUrl: string): string | null {
  const normalized = normalizeVaultUrl(vaultUrl)
  if (!normalized) return null
  return `${normalized}/api/*`
}

/** Absolute URL for an API path under the stored vault. */
export function toApiUrl(vaultUrl: string, path: string): string {
  const normalized = normalizeVaultUrl(vaultUrl)
  if (!normalized) throw new Error('Vault URL is not usable')
  return `${normalized}/api${path.startsWith('/') ? path : `/${path}`}`
}

/**
 * A deep link into the web app, guarded against a tampered stored URL.
 *
 * Returns null when the result would leave the vault's own origin, so this can
 * never become a way to open an arbitrary page.
 */
function toVaultLink(vaultUrl: string, pathAndQuery: string): string | null {
  const normalized = normalizeVaultUrl(vaultUrl)
  if (!normalized) return null

  try {
    const base = new URL(normalized)
    const target = new URL(`${normalized}${pathAndQuery}`)
    return target.origin === base.origin ? target.href : null
  } catch {
    return null
  }
}

/**
 * Where the user approves a pairing. The code is not in the link: the user
 * reads it off the popup and types it into the page. A code that travels in
 * the URL is a code that can be pre-filled by whoever built the URL, and the
 * whole ceremony rests on the user matching what the extension shows against
 * what the page holds. No query and no fragment, so nothing reaches an access
 * log or a screenshot either.
 */
export function toPairingApprovalLink(vaultUrl: string): string | null {
  return toVaultLink(vaultUrl, '/extension/connect')
}

/**
 * "Add a password", opening the web app's create modal for a group.
 *
 * The group *slug* is the group name: `slugifyGroupName` in the web app is
 * currently the identity function, and `findGroupIdBySlug` accepts both the raw
 * and the encoded form. Pinned by a test so that if the web app ever introduces
 * real slugification, this breaks here rather than silently opening the wrong
 * group.
 */
export function toCreatePasswordLink(vaultUrl: string, groupName: string): string | null {
  return toVaultLink(vaultUrl, `/passwords/${encodeURIComponent(groupName)}?create=1`)
}

/** "Edit this password", opening the web app's edit modal. */
export function toEditPasswordLink(
  vaultUrl: string,
  groupName: string,
  entryId: string,
): string | null {
  return toVaultLink(
    vaultUrl,
    `/passwords/${encodeURIComponent(groupName)}?edit=${encodeURIComponent(entryId)}`,
  )
}
