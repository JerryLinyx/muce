'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useMemo } from 'react'
import { useBars } from '@/lib/queries'
import { mergeSearch } from '@/lib/url-state'
import { SymbolSelector } from '@/components/dashboard/SymbolSelector'
import { IndicatorToggles } from '@/components/dashboard/IndicatorToggles'
import { SymbolInfoCard } from '@/components/dashboard/SymbolInfoCard'
import { RecentBarsTable } from '@/components/dashboard/RecentBarsTable'
import { KLineChart } from '@/components/chart/KLineChart'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { TableSkeleton } from '@/components/feedback/TableSkeleton'
import { Skeleton } from '@/components/feedback/Skeleton'

export default function DashboardPage() {
  const router = useRouter()
  const sp = useSearchParams()
  const symbol = sp.get('symbol')
  const adjust = sp.get('adjust') ?? 'qfq'
  const indicatorsParam = sp.get('indicators') ?? 'ma_20'
  const indicators = useMemo(() => indicatorsParam.split(',').filter(Boolean), [indicatorsParam])

  const updateSearch = (overrides: Record<string, string | null>) => {
    const q = mergeSearch(new URLSearchParams(sp.toString()), overrides)
    router.replace(`/dashboard${q ? `?${q}` : ''}`)
  }

  const { data, isLoading, isError, error } = useBars(symbol, {
    adjust,
    indicators: indicators.join(','),
  })

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 44px)' }}>
      <div className="border-b border-border bg-canvas flex items-center gap-3 px-5" style={{ height: 52 }}>
        <SymbolSelector value={symbol} onChange={(s) => updateSearch({ symbol: s })} />
        <div className="inline-flex border border-border rounded-sm overflow-hidden">
          {(['qfq', 'raw'] as const).map((m) => (
            <button
              key={m}
              onClick={() => updateSearch({ adjust: m })}
              className={
                'px-2.5 h-8 text-sm border-r border-border last:border-r-0 ' +
                (adjust === m ? 'bg-accent-soft text-ink' : 'text-ink-soft hover:bg-surface')
              }
            >
              {m === 'qfq' ? '前复权' : '不复权'}
            </button>
          ))}
        </div>
        <IndicatorToggles
          value={indicators}
          onChange={(next) => updateSearch({ indicators: next.join(',') || null })}
        />
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col">
          {!symbol ? (
            <EmptyState title="请先选择标的" hint="点击左上角搜索框,输入 6 位代码或市场后缀(如 000001.SZ)" />
          ) : isLoading ? (
            <div className="flex-1 m-3"><Skeleton className="w-full h-full" /></div>
          ) : isError ? (
            <div className="p-4"><ErrorBanner>{(error as Error).message}</ErrorBanner></div>
          ) : !data || data.rows.length === 0 ? (
            <EmptyState
              title="该标的尚未下载数据"
              hint={<>请运行 <code className="font-mono text-ink">uv run quant-data download --symbols {symbol}</code></>}
            />
          ) : (
            <div className="flex-1">
              <KLineChart rows={data.rows} indicators={indicators} />
            </div>
          )}
        </div>

        <aside className="w-[300px] border-l border-border bg-canvas p-3 space-y-3 overflow-y-auto">
          <SymbolInfoCard symbol={symbol} adjust={adjust} />
          {!data ? <TableSkeleton rows={6} cols={5} /> : <RecentBarsTable rows={data.rows} />}
        </aside>
      </div>
    </div>
  )
}
