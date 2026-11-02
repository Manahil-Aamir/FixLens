import type { Diagnosis, Supported } from './types'
import { File } from 'expo-file-system'

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.1.10:8000'
const TIMEOUT_MS = 60_000

export class ApiError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(API_URL + path, { ...init, signal: controller.signal })
    const text = await res.text()
    let data: any = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      /* not JSON */
    }
    if (!res.ok) {
      const detail = typeof data?.detail === 'string' ? data.detail : 'Something went wrong.'
      throw new ApiError(detail, res.status)
    }
    return data as T
  } catch (e: any) {
    if (e instanceof ApiError) throw e
    console.warn('API request failed:', path, e?.name, e?.message)
    if (e?.name === 'AbortError') {
      throw new ApiError('The server took too long to answer. Please try again.')
    }
    throw new ApiError(
      __DEV__
        ? `Can't reach the server (${API_URL}). ${e?.message ?? ''}`
        : "Can't reach the server. Check your connection and try again.",
    )
  } finally {
    clearTimeout(timer)
  }
}

export function listObjects(): Promise<Supported[]> {
  return request<Supported[]>('/objects')
}

export function createDiagnosis(
  uri: string,
  kind: 'image' | 'video' = 'image',
): Promise<Diagnosis> {
  const form = new FormData()
  const name = kind === 'video' ? 'clip.mp4' : 'photo.jpg'
  // The form field name matches the backend: "image" or "video".
  form.append(kind, new File(uri) as unknown as Blob, name)
  return request<Diagnosis>('/diagnoses', { method: 'POST', body: form })
}

export function sendAnswers(
  id: string,
  answers: { question_id: string; value: string }[],
): Promise<Diagnosis> {
  return request<Diagnosis>(`/diagnoses/${id}/answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
}
