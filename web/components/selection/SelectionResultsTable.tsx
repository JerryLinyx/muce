'use client'

import Link from 'next/link'
import type { SelectionResult } from '@/lib/api-types'
import { Button } from '@/components/ui/Button'
import { downloadCsv } from '@/lib/csv'

const FACTOR_LABELS: Record<string, string> = {
  ma_breakout: '均线突破',
  kdj_golden_cross: 'KDJ金叉',
  macd_golden_cross: 'MACD金叉',
  rsi_momentum: 'RSI动量',
  volume_breakout: '放量',
  boll_breakout: '布林突破',
}

export function SelectionResultsTable({ result }: { result: SelectionResult }) {
  const summary = result.summary
  const candidates = result.candidates

  const exportCsv = () => {
    downloadCsv(`选股_${result.as_of_date}.csv`, candidates.map((c, i) => ({
      序号: i + 1,
      标的: c.symbol,
      因子分: c.score,
      命中因子: c.factors_hit.join(';'),
      理由: c.reasons,
    })))
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="全市场" value={summary.total_universe} />
        <Stat label="过阈值" value={summary.passed_min_score} />
        <Stat label="Top-N" value={summary.top_n_returned} />
      </div>

      <div className="flex items-center justify-between">
        <div className="text-md font-medium">候选股({candidates.length})</div>
        <Button size="sm" variant="ghost" onClick={exportCsv}>导出 CSV</Button>
      </div>

      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface text-ink-soft">
            <tr>
              <th className="text-right px-2 py-2 font-medium">#</th>
              <th className="text-left  px-2 py-2 font-medium">标的</th>
              <th className="text-right px-2 py-2 font-medium">因子分</th>
              <th className="text-left  px-2 py-2 font-medium">命中</th>
              <th className="text-left  px-2 py-2 font-medium">理由</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c, i) => (
              <tr key={c.symbol} className="border-t border-border hover:bg-accent-soft">
                <td className="px-2 py-1.5 numeric text-right text-ink-muted">{i + 1}</td>
                <td className="px-2 py-1.5">
                  <Link href={`/dashboard?symbol=${encodeURIComponent(c.symbol)}`} className="font-mono text-ink hover:underline">
                    {c.symbol}
                  </Link>
                </td>
                <td className="px-2 py-1.5 numeric text-right">{c.score}</td>
                <td className="px-2 py-1.5 space-x-1">
                  {c.factors_hit.map((f) => (
                    <span key={f} className="inline-block px-1.5 py-0.5 text-xs rounded-sm bg-accent-soft text-ink">
                      {FACTOR_LABELS[f] ?? f}
                    </span>
                  ))}
                </td>
                <td className="px-2 py-1.5 text-xs text-ink-soft truncate max-w-[280px]" title={c.reasons}>{c.reasons}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-border rounded-md bg-chart p-3">
      <div className="text-xs text-ink-muted mb-1">{label}</div>
      <div className="text-lg numeric">{value.toLocaleString('en-US')}</div>
    </div>
  )
}
