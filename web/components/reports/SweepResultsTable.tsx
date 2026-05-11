'use client'

import * as React from 'react'
import { Button } from '@/components/ui/Button'
import { fmtNumber, fmtPercent } from '@/lib/format'

type Row = Record<string, unknown>
const METRIC_KEYS = new Set(['total_return', 'sharpe', 'max_drawdown', 'win_rate', 'trades', 'annual_return', 'annual_return_pct', 'max_drawdown_pct'])

function isPercent(key: string): boolean {
  return (key.includes('return') && !key.endsWith('_pct')) || key === 'max_drawdown' || key === 'win_rate'
}

function formatCell(key: string, value: unknown): string {
  if (value == null) return '—'
  if (typeof value !== 'number') return String(value)
  if (isPercent(key)) return fmtPercent(value)
  if (Number.isInteger(value)) return value.toLocaleString('en-US')
  return fmtNumber(value, 3)
}

export function SweepResultsTable({ rows, defaultSort }: { rows: Row[]; defaultSort: string }) {
  const columns = React.useMemo(() => {
    if (rows.length === 0) return []
    return Object.keys(rows[0]!)
  }, [rows])

  const [sortKey, setSortKey] = React.useState<string>(defaultSort)
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('desc')
  const [page, setPage] = React.useState(0)
  const PAGE = 25

  const sorted = React.useMemo(() => {
    const out = [...rows]
    out.sort((a, b) => {
      const va = a[sortKey]; const vb = b[sortKey]
      if (va == null) return 1
      if (vb == null) return -1
      const cmp = typeof va === 'number' && typeof vb === 'number'
        ? va - vb : String(va).localeCompare(String(vb))
      return sortDir === 'asc' ? cmp : -cmp
    })
    return out
  }, [rows, sortKey, sortDir])

  const pageRows = sorted.slice(page * PAGE, (page + 1) * PAGE)
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE))

  return (
    <div className="space-y-2">
      <div className="border border-border rounded-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-surface text-ink-soft">
            <tr>
              {columns.map((c) => {
                const isMetric = METRIC_KEYS.has(c)
                const active = sortKey === c
                return (
                  <th
                    key={c}
                    onClick={() => {
                      if (active) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
                      else { setSortKey(c); setSortDir(isMetric ? 'desc' : 'asc') }
                    }}
                    className={`px-2.5 py-2 cursor-pointer font-medium select-none whitespace-nowrap ${isMetric ? 'text-right' : 'text-left'}`}
                  >
                    {c}{active && (sortDir === 'asc' ? ' ▲' : ' ▼')}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r, i) => (
              <tr key={String(r.combo_id ?? i)} className="border-t border-border hover:bg-accent-soft">
                {columns.map((c) => (
                  <td key={c} className={`px-2.5 py-1.5 numeric ${METRIC_KEYS.has(c) ? 'text-right' : 'text-left'}`}>
                    {formatCell(c, r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-ink-soft">
        <span>共 {sorted.length} 个组合</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>上一页</Button>
          <span>{page + 1} / {totalPages}</span>
          <Button size="sm" variant="ghost" disabled={page >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>下一页</Button>
        </div>
      </div>
    </div>
  )
}
