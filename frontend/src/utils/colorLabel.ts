/**
 * Translates a theme color's internal name (from src/config/colorThemes.ts,
 * e.g. "emerald", "slate") for display, falling back to that raw name for
 * any color not (yet) in the translation tables — so a new palette entry
 * degrades to its technical name instead of showing a raw i18n key.
 */
export function translateColorName(t: (key: string) => string, name: string): string {
  const key = `components.themeSwitcher.colorNames.${name}`
  const translated = t(key)
  return translated === key ? name : translated
}
