import type { Finding, ScanSummary, Severity } from '../types'

class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : `Error ${response.status}`
    throw new ApiError(message)
  }

  return response.json() as Promise<T>
}

export function createScan(path: string): Promise<ScanSummary> {
  return request<ScanSummary>('/scans', {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}

export function listScans(): Promise<ScanSummary[]> {
  return request<ScanSummary[]>('/scans')
}

export function getScan(scanId: number): Promise<ScanSummary> {
  return request<ScanSummary>(`/scans/${scanId}`)
}

export interface FindingFilters {
  severity?: Severity
  module?: string
}

export function getScanFindings(scanId: number, filters: FindingFilters = {}): Promise<Finding[]> {
  const params = new URLSearchParams()
  if (filters.severity) params.set('severity', filters.severity)
  if (filters.module) params.set('module', filters.module)
  const query = params.toString()
  return request<Finding[]>(`/scans/${scanId}/findings${query ? `?${query}` : ''}`)
}

export { ApiError }
