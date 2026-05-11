'use client'

import { use } from 'react'
import Link from 'next/link'
import { useReportDetail, useReportEquity, useReportTrades } from '@/lib/queries'
import { StatGrid, type Stat } from '@/components/reports/StatGrid'
import { TradesTable } from '@/components/reports/TradesTable'
import { EquityChart } from '@/components/chart/EquityChart'
import { MetaPanel } from '@/components/reports/MetaPanel'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { Skeleton } from '@/components/feedback/Skeleton'

export default function ReportDetailPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params)
  const { data: manifest, isLoading, isError, error } = useReportDetail(runId)

  if (isLoading) return <div className="p-5"><Skeleton className="h-6 w-64 mb-3" /><Skeleton className="h-32 w-full" /></div>
  if (isError) return <div className="p-5"><ErrorBanner>{(error as Error).message}</ErrorBanner></div>
  if (!manifest) return null

  const m = manifest as unknown as Record<string, unknown>
  const kind = m.kind as string

  return (
    <div className="p-5 space-y-5">
      <div className="flex items-center gap-3 text-sm">
        <Link href="/reports" className="text-accent hover:underline">{'<'} 返回列表</Link>
        <span className="text-ink-muted">·</span>
        <span className="font-mono text-xs">{runId}</span>
      </div>

      {kind === 'validate' ? <ValidateBranch runId={runId} manifest={m} /> : null}
      {kind === 'sweep' ? <SweepBranchPlaceholder /> : null}

      <MetaPanel manifest={m} />
    </div>
  )
}

function ValidateBranch({ runId, manifest }: { runId: string; manifest: Record<string, unknown> }) {
  const summary = (manifest.summary_metrics ?? {}) as Record<string, number>
  const stats: Stat[] = [
    { label: '总收益', value: summary.total_return, format: 'percent', tone: 'auto' },
    { label: '夏普', value: summary.sharpe, format: 'number', decimals: 2 },
    { label: '最大回撤', value: summary.max_drawdown, format: 'percent', tone: 'auto' },
    { label: '交易数', value: summary.trades ?? summary.trade_count, format: 'int' },
  ]
  const equity = useReportEquity(runId)
  const trades = useReportTrades(runId)
  return (
    <>
      <div className="text-md text-ink-soft">
        策略:{String(manifest.strategy ?? '—')} · 信号 {String(manifest.signal_adjust ?? '—')} / 执行 {String(manifest.execution_adjust ?? '—')}
      </div>
      <StatGrid stats={stats} />
      {equity.isLoading ? <Skeleton className="h-[360px] w-full" /> :
        equity.data ? <EquityChart rows={equity.data.rows as Record<string, unknown>[]} /> :
        null}
      <div>
        <div className="text-md font-medium mb-2">交易明细</div>
        {trades.isLoading ? <Skeleton className="h-40 w-full" /> :
          trades.data ? <TradesTable rows={trades.data.rows as Record<string, unknown>[]} /> :
          null}
      </div>
    </>
  )
}

function SweepBranchPlaceholder() {
  return <div className="text-ink-soft text-sm">(Sweep 详情见 Milestone E)</div>
}
