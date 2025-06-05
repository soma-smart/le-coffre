import { like } from 'drizzle-orm'
import { folder } from '~/server/database/schema'
import { useDatabase } from '~/server/utils/useDatabase'
/**
 * Génère un slug unique à partir d'un nom
 * @param name - Le nom à partir duquel générer le slug
 * @returns Le slug généré
 */
export async function generateUniqueSlug(
  name: string,
): Promise<string> {
  // Génération du slug de base à partir du nom
  const baseSlug = name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-') // Remplace les espaces par des tirets
    .replace(/[^\w-]+/g, '') // Supprime les caractères spéciaux

  // Vérifier si le slug de base existe déjà
  const existingSlugs = useDatabase().select().from(folder).where(like(folder.slug, `${baseSlug}%`)).all()

  // Si aucun slug similaire n'existe, retourner le slug de base
  if (existingSlugs.length === 0) {
    return baseSlug
  }

  // Créer un ensemble des slugs existants pour une recherche rapide
  const existingSlugSet = new Set(existingSlugs.map(row => row.slug))

  // Si le slug de base lui-même n'existe pas, le retourner
  if (!existingSlugSet.has(baseSlug)) {
    return baseSlug
  }

  // Trouver le premier suffixe numérique disponible sans limite à 1000
  let i = 1
  while (true) {
    const slugWithSuffix = `${baseSlug}-${i}`
    if (!existingSlugSet.has(slugWithSuffix)) {
      return slugWithSuffix
    }
    i++
  }
}
