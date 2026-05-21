const HTTP_PROTOCOLS = new Set(['http:', 'https:'])

export const normalizeExternalHttpUrl = (value: string | null | undefined): string | null => {
  const trimmed = value?.trim()
  if (!trimmed) {
    return null
  }

  try {
    const url = new URL(trimmed)
    return HTTP_PROTOCOLS.has(url.protocol) && !!url.hostname ? url.href : null
  } catch {
    return null
  }
}

export const isSafeHttpUrl = (value: string | null | undefined): boolean =>
  normalizeExternalHttpUrl(value) !== null
