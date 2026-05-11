/**
 * Thin domain types for the Muce API responses.
 *
 * The generated `api-generated.ts` reflects FastAPI's path/operation map,
 * but the backend returns untyped `dict` objects so the generated response
 * types are `{ [key: string]: unknown }`. These hand-rolled types describe
 * the actual JSON shapes the backend emits.
 *
 * Regenerate `api-generated.ts` (`npm run gen:api`) any time backend
 * endpoints change; consult this file and update it to match.
 */

// ──────────────── data router ────────────────

export interface SymbolRow {
  symbol: string
  market: string
  last_cached_date: string | null
}

export interface SymbolInfo {
  symbol: string
  market: string
  last_cached_date: string | null
}

export interface BarRow {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  // Indicators (optional, present when requested)
  [indicator: string]: number | string | undefined | null
}

export interface BarsData {
  symbol: string
  adjust: string
  indicators_requested: string[]
  rows: BarRow[]
}

export interface CoverageEntry {
  symbol: string
  rows: number
  first_date: string | null
  last_date: string | null
}

// ──────────────── selection router ────────────────

export interface Factor {
  key: string
  name_cn: string
  description: string
}

export interface FactorConfig {
  ma_short: number
  ma_long: number
  kdj_window: number
  macd_fast: number
  macd_slow: number
  macd_signal: number
  rsi_window: number
  rsi_threshold: number
  volume_window: number
  volume_multiplier: number
  boll_window: number
  boll_std: number
  min_score: number
  top_n: number
  exclude_suspended: boolean
  exclude_st: boolean
  require_factors: string[]
  exclude_factors: string[]
}

export interface SelectionJobRequest {
  as_of_date?: string | null
  config?: Partial<FactorConfig> & Record<string, unknown>
  symbol_universe?: string[] | null
}

export interface SelectionCandidate {
  symbol: string
  score: number
  factors_hit: string[]
  reasons: string
}

export interface SelectionSummary {
  total_universe: number
  passed_min_score: number
  top_n_returned: number
}

export interface SelectionResult {
  as_of_date: string
  config: Record<string, unknown>
  candidates: SelectionCandidate[]
  summary: SelectionSummary
}

export interface JobState {
  job_id: string
  status: 'pending' | 'running' | 'done' | 'failed'
  stage: string | null
  progress: number
  message: string
  result: SelectionResult | null
  error: string | null
}

// ──────────────── reports router ────────────────

export interface DateRange {
  start: string
  end: string
}

export interface ArtifactRef {
  name: string
  path: string
  rows: number
}

export interface ReportManifest {
  run_id: string
  kind: 'sweep' | 'validate'
  created_at: string
  elapsed_seconds: number
  git_commit: string | null
  git_dirty: boolean
  data_range: DateRange
  symbols: string[]
  config_hash: string
  config_path: string
  artifacts: ArtifactRef[]
  // Sweep-specific:
  strategy?: string
  grid_size?: number
  rank_by?: string
  top_combos?: Record<string, unknown>[]
  // Validate-specific:
  signal_adjust?: string
  execution_adjust?: string
  summary_metrics?: Record<string, number>
}

export type ReportDetail = ReportManifest

export interface ArtifactRows {
  name: string
  rows: Record<string, unknown>[]
}

// ──────────────── system ────────────────

export interface HealthStatus {
  status: string
  cache_root_exists: boolean
  reports_dir_exists: boolean
}

export interface VersionInfo {
  version: string
  provider: string
}
