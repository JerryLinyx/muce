'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useReports } from '@/lib/queries'
import { mergeSearch } from '@/lib/url-state'
import { ReportListTable } from '@/components/reports/ReportListTable'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { TableSkeleton } from '@/components/feedback/TableSkeleton'

const KINDS = [
  { key: '', label: '全部' },
  { key: 'sweep', label: 'Sweep' },
  { key: 'validate', label: 'Validate' },
] as const

export default function ReportsPage() {
  const router = useRouter()
  const sp = useSearchParams()
  const kind = sp.get('kind') ?? ''
  const since = sp.get('since') ?? ''

  const update = (overrides: Record<string, string | null>) => {
    const q = mergeSearch(new URLSearchParams(sp.toString()), overrides)
    router.replace(`/reports${q ? `?${q}` : ''}`)
  }

  const { data, isLoading, isError, error } = useReports(kind || undefined, since || undefined)

  return (
    <div className="flex flex-col">
      <div className="border-b border-border bg-canvas flex items-center gap-3 px-5" style={{ height: 52 }}>
        <div className="inline-flex border border-border rounded-sm overflow-hidden">
          {KINDS.map((k) => (
            <button
              key={k.key}
              onClick={() => update({ kind: k.key || null })}
              className={
                'px-2.5 h-8 text-sm border-r border-border last:border-r-0 ' +
                ((kind || '') === k.key ? 'bg-accent-soft text-ink' : 'text-ink-soft hover:bg-surface')
              }
            >
              {k.label}
            </button>
          ))}
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-ink-soft">
          自:
          <input
            type="date"
            value={since}
            onChange={(e) => update({ since: e.target.value || null })}
            className="h-8 px-2 rounded-sm border border-border bg-canvas text-sm"
          />
        </label>
      </div>

      <div className="p-5">
        {isLoading ? (
          <TableSkeleton rows={6} cols={7} />
        ) : isError ? (
          <ErrorBanner>{(error as Error).message}</ErrorBanner>
        ) : !data || data.length === 0 ? (
          <EmptyState
            title="还没有报告"
            hint={<>运行 <code className="font-mono text-ink">uv run quant-backtest sweep …</code> 或 <code className="font-mono text-ink">validate …</code> 生成。</>}
          />
        ) : (
          <ReportListTable rows={data} />
        )}
      </div>
    </div>
  )
}
