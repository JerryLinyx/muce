'use client'

import { useSymbolInfo } from '@/lib/queries'
import { Skeleton } from '@/components/feedback/Skeleton'

export function SymbolInfoCard({ symbol, adjust }: { symbol: string | null; adjust: string }) {
  const { data, isLoading } = useSymbolInfo(symbol, adjust)
  return (
    <div className="border border-border rounded-md bg-chart p-4">
      <div className="text-xs text-ink-muted mb-1">标的信息</div>
      {isLoading ? (
        <div className="space-y-2"><Skeleton className="h-4 w-32" /><Skeleton className="h-3 w-24" /></div>
      ) : data ? (
        <div className="space-y-1.5">
          <div className="text-md font-medium font-mono">{data.symbol}</div>
          <div className="text-sm text-ink-soft">市场:{data.market}</div>
          <div className="text-sm text-ink-soft">最新数据:{data.last_cached_date ?? '—'}</div>
        </div>
      ) : (
        <div className="text-sm text-ink-muted">未选择标的</div>
      )}
    </div>
  )
}
