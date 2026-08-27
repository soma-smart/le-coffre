/**
 * The only way the popup talks to the service worker.
 *
 * The popup never calls the API itself, enforced by eslint. All network lives
 * in the worker: the popup is destroyed on any outside click and would abort a
 * reveal whose audit event the server has already written.
 */
import type { AppError, Result } from '@/domain/errors'
import { chromeBrowser } from '@/platform/chrome'
import type { PayloadFor, Request, RequestType } from '@/shared/messages'

export async function send<T extends RequestType>(
  request: Extract<Request, { type: T }>,
): Promise<Result<PayloadFor<T>>> {
  try {
    const response = (await chromeBrowser.runtime.sendMessage(request)) as
      Result<PayloadFor<T>> | undefined

    if (!response) {
      // The worker died mid-flight, or nothing answered.
      return { ok: false, error: { kind: 'SERVER_ERROR', status: 0 } }
    }
    return response
  } catch (caught) {
    return {
      ok: false,
      error: {
        kind: 'SERVER_ERROR',
        status: 0,
        detail: caught instanceof Error ? caught.message : 'the extension worker did not answer',
      },
    }
  }
}

/**
 * Request the host permission for a vault.
 *
 * MUST be called synchronously from a click handler. Any `await` before this
 * consumes the user gesture and Chrome rejects the call with "This function
 * must be called during a user gesture". Validate inside the resolution, never
 * before.
 */
export function requestHostPermission(matchPattern: string): Promise<boolean> {
  return chromeBrowser.permissions.request([matchPattern])
}

export function hasHostPermission(matchPattern: string): Promise<boolean> {
  return chromeBrowser.permissions.contains([matchPattern])
}

export function openTab(url: string): void {
  void chromeBrowser.tabs.create(url)
}

export type { AppError }
