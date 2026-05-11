'use client'

import * as React from 'react'
import { useSubmitSelectionJob } from '@/lib/queries'
import { useSelectionJobStream } from '@/lib/sse'
import { useToast } from '@/components/ui/Toast'
import { FactorConfigPanel, type SelectionFormValues } from '@/components/selection/FactorConfigPanel'
import { ProgressIndicator } from '@/components/selection/ProgressIndicator'
import { SelectionResultsTable } from '@/components/selection/SelectionResultsTable'
import { ErrorBanner } from '@/components/feedback/ErrorBanner'
import { EmptyState } from '@/components/feedback/EmptyState'

export default function SelectionPage() {
  const [panelOpen, setPanelOpen] = React.useState(true)
  const [jobId, setJobId] = React.useState<string | null>(null)
  const [runStart, setRunStart] = React.useState<number | null>(null)
  const [slowNow, setSlowNow] = React.useState(false)
  const submit = useSubmitSelectionJob()
  const stream = useSelectionJobStream(jobId)
  const toast = useToast()

  React.useEffect(() => {
    if (stream.status !== 'running') { setSlowNow(false); return }
    if (runStart === null) return
    const id = setInterval(() => {
      setSlowNow(Date.now() - runStart > 15_000)
    }, 1_000)
    return () => clearInterval(id)
  }, [stream.status, runStart])

  const onSubmit = (values: SelectionFormValues) => {
    const body = {
      as_of_date: values.as_of_date || null,
      config: {
        min_score: values.min_score,
        top_n: values.top_n,
        exclude_suspended: values.exclude_suspended,
        exclude_st: values.exclude_st,
        require_factors: values.require_factors,
        exclude_factors: values.exclude_factors,
        ma_short: values.ma_short,
        ma_long: values.ma_long,
        rsi_window: values.rsi_window,
        rsi_threshold: values.rsi_threshold,
        volume_window: values.volume_window,
        volume_multiplier: values.volume_multiplier,
      },
      symbol_universe: null,
    }
    setRunStart(Date.now())
    submit.mutate(body, {
      onSuccess: ({ job_id }) => setJobId(job_id),
      onError: (err: Error) => toast.add({ tone: 'error', title: '提交失败', description: err.message }),
    })
  }

  const running = stream.status === 'running'

  return (
    <div className="flex" style={{ height: 'calc(100vh - 44px)' }}>
      {panelOpen && (
        <aside className="w-[320px] border-r border-border bg-canvas overflow-y-auto">
          <div className="px-4 pt-3 flex items-center justify-between">
            <div className="text-xs uppercase tracking-wide text-ink-muted">选股配置</div>
            <button
              onClick={() => setPanelOpen(false)}
              className="text-xs text-ink-soft hover:text-ink"
              aria-label="收起"
            >
              收起 ←
            </button>
          </div>
          <FactorConfigPanel onSubmit={onSubmit} disabled={running} />
        </aside>
      )}

      <div className="flex-1 overflow-y-auto">
        {!panelOpen && (
          <div className="px-5 pt-3">
            <button
              onClick={() => setPanelOpen(true)}
              className="text-xs text-ink-soft hover:text-ink"
              aria-label="展开"
            >
              → 展开配置
            </button>
          </div>
        )}

        <div className="p-5">
          {stream.status === 'idle' && (
            <EmptyState title="配置好因子后点开始选股" hint="左侧面板调整截止日期与因子参数,默认值适合一般情况。" />
          )}

          {stream.status === 'running' && (
            <ProgressIndicator
              stage={stream.stage}
              progress={stream.progress}
              message={stream.message}
              slow={slowNow}
            />
          )}

          {stream.status === 'done' && <SelectionResultsTable result={stream.result} />}

          {stream.status === 'failed' && <ErrorBanner>{stream.error}</ErrorBanner>}
        </div>
      </div>
    </div>
  )
}
