import { describe, expect, it, vi, beforeEach } from 'vitest'
import { generateUniqueSlug } from '~/server/utils/folder/generateSlug'
import { useDatabase } from '~/server/utils/useDatabase'

// Mock database module
vi.mock('~/server/utils/useDatabase', () => ({
  useDatabase: vi.fn(),
}))

describe('generateUniqueSlug', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('should generate a basic slug from a folder name', async () => {
    // Mock empty database response (no existing slugs)
    const mockSelect = vi.fn().mockReturnThis()
    const mockFrom = vi.fn().mockReturnThis()
    const mockWhere = vi.fn().mockReturnThis()
    const mockAll = vi.fn().mockReturnValue([])

    vi.mocked(useDatabase).mockReturnValue({
      select: mockSelect,
      from: mockFrom,
      where: mockWhere,
      all: mockAll,
    } as any)

    const slug = await generateUniqueSlug('Test Folder')
    expect(slug).toBe('test-folder')
  })

  it('should generate a unique slug when a duplicate exists', async () => {
    // Mock database with existing slug
    const mockSelect = vi.fn().mockReturnThis()
    const mockFrom = vi.fn().mockReturnThis()
    const mockWhere = vi.fn().mockReturnThis()
    const mockAll = vi.fn().mockReturnValue([
      { slug: 'test-folder' },
    ])

    vi.mocked(useDatabase).mockReturnValue({
      select: mockSelect,
      from: mockFrom,
      where: mockWhere,
      all: mockAll,
    } as any)

    const slug = await generateUniqueSlug('Test Folder')
    expect(slug).toBe('test-folder-1')
  })

  it('should handle special characters in folder names', async () => {
    // Mock empty database response
    const mockSelect = vi.fn().mockReturnThis()
    const mockFrom = vi.fn().mockReturnThis()
    const mockWhere = vi.fn().mockReturnThis()
    const mockAll = vi.fn().mockReturnValue([])

    vi.mocked(useDatabase).mockReturnValue({
      select: mockSelect,
      from: mockFrom,
      where: mockWhere,
      all: mockAll,
    } as any)

    const slug = await generateUniqueSlug('Test & Folder #123!')
    expect(slug).toBe('test-folder-123')
  })

  it('should find the next available number for a slug', async () => {
    // Mock database with multiple existing slugs
    const mockSelect = vi.fn().mockReturnThis()
    const mockFrom = vi.fn().mockReturnThis()
    const mockWhere = vi.fn().mockReturnThis()
    const mockAll = vi.fn().mockReturnValue([
      { slug: 'test-folder' },
      { slug: 'test-folder-1' },
      { slug: 'test-folder-2' },
    ])

    vi.mocked(useDatabase).mockReturnValue({
      select: mockSelect,
      from: mockFrom,
      where: mockWhere,
      all: mockAll,
    } as any)

    const slug = await generateUniqueSlug('Test Folder')
    expect(slug).toBe('test-folder-3')
  })
})
