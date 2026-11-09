import type { AnalyzeRequest, AnalyzeResult, Place } from './types'

const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new Error('Cannot reach the server. Please try again.')
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = body?.error ?? (typeof body === 'object' ? Object.values(body).flat().join(' ') : '')
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return body as T
}

export const geocode = (q: string, signal?: AbortSignal) =>
  request<Place[]>(`/api/geocode?q=${encodeURIComponent(q)}`, { signal })

export const analyze = (payload: AnalyzeRequest) =>
  request<AnalyzeResult>('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
