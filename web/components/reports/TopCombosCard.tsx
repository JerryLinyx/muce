import { fmtPercent, fmtNumber } from '@/lib/format'

const METRIC_KEYS = new Set(['total_return', 'sharpe', 'max_drawdown', 'win_rate', 'trades', 'annual_return', 'annual_return_pct', 'max_drawdown_pct'])

export function TopCombosCard({ combos, rankBy }: { combos: Record<string, unknown>[]; rankBy: string }) {
  if (!combos || combos.length === 0) return null
  return (
    <div className="border border-border rounded-md bg-chart p-4 space-y-2">
      <div className="text-md font-medium">Top {combos.length} 组合(按 {rankBy} 排序)</div>
      <ol className="space-y-1.5">
        {combos.map((c, i) => {
          const score = c[rankBy] as number | undefined
          const params = Object.entries(c).filter(
            ([k]) => k !== 'combo_id' && k !== rankBy && !METRIC_KEYS.has(k)
          )
          const isPct = rankBy.includes('return') || rankBy.includes('drawdown')
          return (
            <li key={String(c.combo_id ?? i)} className="text-sm flex items-baseline gap-3">
              <span className="text-ink-muted text-xs numeric w-5 text-right">{i + 1}.</span>
              <span className="numeric font-medium w-20 text-right">
                {isPct ? fmtPercent(score) : fmtNumber(score)}
              </span>
              <span className="text-xs text-ink-soft truncate">
                {params.map(([k, v]) => `${k}=${v}`).join(' · ') || '—'}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
