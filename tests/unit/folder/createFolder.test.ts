import { describe, expect, it, vi, beforeEach } from 'vitest'
import { createFolderService } from '~/server/utils/folder/createFolder'
import { generateUniqueSlug } from '~/server/utils/folder/generateSlug'
import { useDatabase } from '~/server/utils/useDatabase'

// Mock dependencies
vi.mock('~/server/utils/folder/generateSlug')
vi.mock('~/server/utils/useDatabase')
vi.mock('consola', () => ({
  consola: {
    error: vi.fn(),
  },
}))

describe('createFolderService', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('should create a folder successfully', async () => {
    // Mock slug generation
    vi.mocked(generateUniqueSlug).mockResolvedValue('test-folder')

    // Mock database operations
    const mockInsert = vi.fn().mockReturnThis()
    const mockValues = vi.fn().mockReturnThis()
    const mockReturning = vi.fn().mockResolvedValue([
      {
        id: 1,
        owner_id: 'user-123',
        name: 'Test Folder',
        slug: 'test-folder',
        icon: 'i-lucide-folder',
        color: '#4f46e5',
      },
    ])

    vi.mocked(useDatabase).mockReturnValue({
      insert: mockInsert,
      values: mockValues,
      returning: mockReturning,
    } as any)

    // Call the service
    const result = await createFolderService.createFolder('user-123', 'Test Folder')

    // Verify the result
    expect(result).toEqual({
      success: true,
    })

    // Verify function calls
    expect(generateUniqueSlug).toHaveBeenCalledWith('Test Folder')
    expect(mockInsert).toHaveBeenCalled()
    expect(mockValues).toHaveBeenCalledWith({
      owner_id: 'user-123',
      name: 'Test Folder',
      slug: 'test-folder',
      icon: 'i-lucide-folder',
      color: '#4f46e5',
    })
    expect(mockReturning).toHaveBeenCalled()
  })

  it('should throw an error when database operation fails', async () => {
    // Mock slug generation
    vi.mocked(generateUniqueSlug).mockResolvedValue('test-folder')

    // Mock database error
    const mockInsert = vi.fn().mockReturnThis()
    const mockValues = vi.fn().mockReturnThis()
    const mockReturning = vi.fn().mockRejectedValue(new Error('Database error'))

    vi.mocked(useDatabase).mockReturnValue({
      insert: mockInsert,
      values: mockValues,
      returning: mockReturning,
    } as any)

    // Call the service and expect error
    await expect(createFolderService.createFolder('user-123', 'Test Folder'))
      .rejects.toThrow('Database error')
  })
})
