import type {
  ArtifactRows,
  BarsData,
  CoverageEntry,
  Factor,
  FactorConfig,
  HealthStatus,
  JobState,
  ReportDetail,
  ReportManifest,
  SelectionJobRequest,
  SymbolInfo,
  SymbolRow,
  VersionInfo,
} from './api-types'

export class ApiError extends Error {
  readonly name = 'ApiError'
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message)
  }
}

type Envelope<T> = { data: T; meta: Record<string, unknown> }

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  })
  let body: unknown
  try {
    body = await res.json()
  } catch {
    body = undefined
  }
  if (!res.ok) {
    const errBody = (body as { error?: { code?: string; message?: string; details?: unknown } } | undefined)?.error
    throw new ApiError(
      errBody?.code ?? 'unknown',
      errBody?.message ?? res.statusText ?? 'request failed',
      res.status,
      errBody?.details,
    )
  }
  return (body as Envelope<T>).data
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export interface BarsOpts {
  adjust?: string
  start?: string
  end?: string
  indicators?: string  // comma-separated
}

export const api = {
  // system
  health: () => http<HealthStatus>('/api/health'),
  version: () => http<VersionInfo>('/api/version'),

  // data
  listSymbols: (opts: { q?: string; market?: string; limit?: number; offset?: number; adjust?: string } = {}) =>
    http<SymbolRow[]>(`/api/symbols${qs(opts)}`),
  symbolInfo: (symbol: string, adjust = 'qfq') =>
    http<SymbolInfo>(`/api/symbols/${encodeURIComponent(symbol)}${qs({ adjust })}`),
  bars: (symbol: string, opts: BarsOpts = {}) =>
    http<BarsData>(`/api/bars/${encodeURIComponent(symbol)}${qs(opts as Record<string, string | undefined>)}`),
  cacheCoverage: (adjust = 'qfq') => http<CoverageEntry[]>(`/api/cache/coverage${qs({ adjust })}`),

  // selection
  factors: () => http<Factor[]>('/api/selection/factors'),
  defaults: () => http<FactorConfig>('/api/selection/defaults'),
  submitSelectionJob: (body: SelectionJobRequest) =>
    http<{ job_id: string }>('/api/selection/jobs', { method: 'POST', body: JSON.stringify(body) }),
  jobStatus: (id: string) =>
    http<JobState>(`/api/selection/jobs/${encodeURIComponent(id)}`),

  // reports
  listReports: (opts: { kind?: string; since?: string; limit?: number } = {}) =>
    http<ReportManifest[]>(`/api/reports${qs(opts as Record<string, string | number | undefined>)}`),
  reportDetail: (id: string) => http<ReportDetail>(`/api/reports/${encodeURIComponent(id)}`),
  reportEquity: (id: string) => http<ArtifactRows>(`/api/reports/${encodeURIComponent(id)}/equity`),
  reportTrades: (id: string) => http<ArtifactRows>(`/api/reports/${encodeURIComponent(id)}/trades`),
  reportSweep: (id: string) => http<ArtifactRows>(`/api/reports/${encodeURIComponent(id)}/sweep`),
}
