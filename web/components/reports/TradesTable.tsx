'use client'

import * as React from 'react'
import { Button } from '@/components/ui/Button'
import { fmtNumber, fmtPercent, fmtDate } from '@/lib/format'

type Row = Record<string, unknown>

const COLUMNS: { key: string; label: string; align: 'left' | 'right'; format: 'date' | 'num' | 'pct' | 'int' | 'text' }[] = [
  { key: 'trade_id', label: 'ID', align: 'right', format: 'int' },
  { key: 'symbol', label: '标的', align: 'left', format: 'text' },
  { key: 'direction', label: '方向', align: 'left', format: 'text' },
  { key: 'open_date', label: '开仓', align: 'left', format: 'date' },
  { key: 'close_date', label: '平仓', align: 'left', format: 'date' },
  { key: 'open_price', label: '开仓价', align: 'right', format: 'num' },
  { key: 'close_price', label: '平仓价', align: 'right', format: 'num' },
  { key: 'size', label: '数量', align: 'right', format: 'int' },
  { key: 'pnl', label: '盈亏', align: 'right', format: 'num' },
  { key: 'pnl_pct', label: '收益率', align: 'right', format: 'pct' },
]

function formatCell(value: unknown, fmt: typeof COLUMNS[number]['format']): string {
  if (value == null) return '—'
  if (fmt === 'date') return fmtDate(String(value))
  if (fmt === 'num') return fmtNumber(Number(value), 2)
  if (fmt === 'int') return Math.round(Number(value)).toLocaleString('en-US')
  if (fmt === 'pct') return fmtPercent(Number(value))
  return String(value)
}

export function TradesTable({ rows }: { rows: Row[] }) {
  const [sortKey, setSortKey] = React.useState<string>('trade_id')
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc')
  const [page, setPage] = React.useState(0)
  const PAGE = 20

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
      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface text-ink-soft">
            <tr>
              {COLUMNS.map((c) => {
                const active = sortKey === c.key
                return (
                  <th
                    key={c.key}
                    onClick={() => {
                      if (active) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
                      else { setSortKey(c.key); setSortDir('asc') }
                    }}
                    className={`px-2.5 py-2 cursor-pointer font-medium select-none ` +
                      (c.align === 'right' ? 'text-right' : 'text-left')}
                  >
                    {c.label}{active && (sortDir === 'asc' ? ' ▲' : ' ▼')}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r, i) => (
              <tr key={`${(r.trade_id as string | number | undefined) ?? i}-${i}`} className="border-t border-border hover:bg-accent-soft">
                {COLUMNS.map((c) => (
                  <td key={c.key} className={`px-2.5 py-1.5 numeric ` + (c.align === 'right' ? 'text-right' : 'text-left')}>
                    {formatCell(r[c.key], c.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-ink-soft">
        <span>共 {sorted.length} 条</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>上一页</Button>
          <span>{page + 1} / {totalPages}</span>
          <Button size="sm" variant="ghost" disabled={page >= totalPages - 1} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}>下一页</Button>
        </div>
      </div>
    </div>
  )
}
