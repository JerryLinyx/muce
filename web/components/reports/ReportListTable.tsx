'use client'

import Link from 'next/link'
import type { ReportManifest } from '@/lib/api-types'
import { fmtNumber } from '@/lib/format'

export function ReportListTable({ rows }: { rows: ReportManifest[] }) {
  if (rows.length === 0) return null
  return (
    <div className="border border-border rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-surface text-ink-soft">
          <tr>
            <th className="text-left px-3 py-2 font-medium">run_id</th>
            <th className="text-left px-3 py-2 font-medium">类型</th>
            <th className="text-left px-3 py-2 font-medium">策略</th>
            <th className="text-right px-3 py-2 font-medium">标的数</th>
            <th className="text-right px-3 py-2 font-medium">用时(s)</th>
            <th className="text-left px-3 py-2 font-medium">创建时间</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id} className="border-t border-border hover:bg-accent-soft">
              <td className="px-3 py-2 font-mono text-xs">{r.run_id.slice(0, 24)}</td>
              <td className="px-3 py-2">{r.kind}</td>
              <td className="px-3 py-2">{r.strategy ?? '—'}</td>
              <td className="px-3 py-2 numeric text-right">{r.symbols.length}</td>
              <td className="px-3 py-2 numeric text-right">{fmtNumber(r.elapsed_seconds, 1)}</td>
              <td className="px-3 py-2 numeric">{r.created_at.replace('T', ' ').replace('Z', '')}</td>
              <td className="px-3 py-2 text-right">
                <Link href={`/reports/${r.run_id}`} className="text-accent hover:underline">详情 →</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
