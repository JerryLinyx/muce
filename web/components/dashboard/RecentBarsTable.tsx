'use client'

import type { BarRow } from '@/lib/api-types'
import { fmtNumber, fmtPercent, fmtCompactNumber, fmtDate } from '@/lib/format'

export function RecentBarsTable({ rows }: { rows: BarRow[] }) {
  const tail = rows.slice(-10).reverse()
  return (
    <div className="border border-border rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-surface text-ink-soft">
          <tr>
            <th className="text-left  px-2 py-2 font-medium">日期</th>
            <th className="text-right px-2 py-2 font-medium">开</th>
            <th className="text-right px-2 py-2 font-medium">高</th>
            <th className="text-right px-2 py-2 font-medium">低</th>
            <th className="text-right px-2 py-2 font-medium">收</th>
            <th className="text-right px-2 py-2 font-medium">涨跌</th>
            <th className="text-right px-2 py-2 font-medium">成交量</th>
          </tr>
        </thead>
        <tbody>
          {tail.map((r, i) => {
            const prev = tail[i + 1]
            const close = r.close as number
            const prevClose = prev ? (prev.close as number) : null
            const pct = prevClose !== null ? (close - prevClose) / prevClose : null
            const tone = pct === null ? '' : pct >= 0 ? 'text-up' : 'text-down'
            return (
              <tr key={String(r.date)} className="border-t border-border hover:bg-accent-soft">
                <td className="px-2 py-1.5 numeric">{fmtDate(String(r.date))}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.open as number)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.high as number)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(r.low as number)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtNumber(close)}</td>
                <td className={`px-2 py-1.5 numeric text-right ${tone}`}>{fmtPercent(pct)}</td>
                <td className="px-2 py-1.5 numeric text-right">{fmtCompactNumber(r.volume as number)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
