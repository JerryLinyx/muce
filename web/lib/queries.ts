import { useQuery, useMutation } from '@tanstack/react-query'
import { api, type BarsOpts } from './api'
import type { SelectionJobRequest } from './api-types'

export const queryKeys = {
  health: () => ['health'] as const,
  symbols: (q?: string, market?: string) => ['symbols', { q: q ?? '', market: market ?? '' }] as const,
  symbolInfo: (symbol: string, adjust = 'qfq') => ['symbol-info', symbol, adjust] as const,
  bars: (symbol: string, opts: BarsOpts) => ['bars', symbol, opts] as const,
  coverage: (adjust = 'qfq') => ['cache-coverage', adjust] as const,

  factors: () => ['selection', 'factors'] as const,
  defaults: () => ['selection', 'defaults'] as const,
  job: (id: string) => ['selection', 'jobs', id] as const,

  reports: (kind?: string, since?: string) => ['reports', { kind: kind ?? '', since: since ?? '' }] as const,
  report: (id: string) => ['reports', id] as const,
  reportEquity: (id: string) => ['reports', id, 'equity'] as const,
  reportTrades: (id: string) => ['reports', id, 'trades'] as const,
  reportSweep: (id: string) => ['reports', id, 'sweep'] as const,
}

export const useHealth = () =>
  useQuery({ queryKey: queryKeys.health(), queryFn: api.health, staleTime: 30_000 })

export const useSymbols = (q?: string, market?: string) =>
  useQuery({
    queryKey: queryKeys.symbols(q, market),
    queryFn: () => api.listSymbols({ q, market, limit: 50 }),
    staleTime: 5 * 60_000,
  })

export const useSymbolInfo = (symbol: string | null, adjust = 'qfq') =>
  useQuery({
    queryKey: symbol ? queryKeys.symbolInfo(symbol, adjust) : ['symbol-info', 'idle'],
    queryFn: () => api.symbolInfo(symbol!, adjust),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  })

export const useBars = (symbol: string | null, opts: BarsOpts) =>
  useQuery({
    queryKey: symbol ? queryKeys.bars(symbol, opts) : ['bars', 'idle'],
    queryFn: () => api.bars(symbol!, opts),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  })

export const useFactors = () =>
  useQuery({ queryKey: queryKeys.factors(), queryFn: api.factors, staleTime: Infinity })

export const useDefaults = () =>
  useQuery({ queryKey: queryKeys.defaults(), queryFn: api.defaults, staleTime: Infinity })

export const useSubmitSelectionJob = () =>
  useMutation({ mutationFn: (body: SelectionJobRequest) => api.submitSelectionJob(body) })

export const useReports = (kind?: string, since?: string) =>
  useQuery({
    queryKey: queryKeys.reports(kind, since),
    queryFn: () => api.listReports({ kind, since }),
    staleTime: 30_000,
  })

export const useReportDetail = (id: string) =>
  useQuery({ queryKey: queryKeys.report(id), queryFn: () => api.reportDetail(id), staleTime: Infinity })

export const useReportEquity = (id: string) =>
  useQuery({ queryKey: queryKeys.reportEquity(id), queryFn: () => api.reportEquity(id), staleTime: Infinity })

export const useReportTrades = (id: string) =>
  useQuery({ queryKey: queryKeys.reportTrades(id), queryFn: () => api.reportTrades(id), staleTime: Infinity })

export const useReportSweep = (id: string) =>
  useQuery({ queryKey: queryKeys.reportSweep(id), queryFn: () => api.reportSweep(id), staleTime: Infinity })
