import { fmtNumber, fmtPercent } from '@/lib/format'

export interface Stat {
  label: string
  value: number | null | undefined
  format: 'percent' | 'number' | 'int'
  tone?: 'auto' | 'neutral'
  decimals?: number
}

export function StatGrid({ stats }: { stats: Stat[] }) {
  return (
    <div className="grid grid-cols-4 gap-3">
      {stats.map((s) => {
        let display: string
        let tone = 'text-ink'
        if (s.value == null) {
          display = '—'
        } else if (s.format === 'percent') {
          display = fmtPercent(s.value, s.decimals ?? 2)
          if (s.tone === 'auto') tone = s.value >= 0 ? 'text-up' : 'text-down'
        } else if (s.format === 'int') {
          display = Math.round(s.value).toLocaleString('en-US')
        } else {
          display = fmtNumber(s.value, s.decimals ?? 2)
        }
        return (
          <div key={s.label} className="border border-border rounded-md bg-chart p-3">
            <div className="text-xs text-ink-muted mb-1">{s.label}</div>
            <div className={`text-stat numeric ${tone}`}>{display}</div>
          </div>
        )
      })}
    </div>
  )
}
