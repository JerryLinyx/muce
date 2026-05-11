const STAGE_LABELS: Record<string, string> = {
  pending: '提交中',
  load_panel: '加载缓存面板',
  compute_indicators: '计算技术指标',
  score: '因子打分',
  filter_rank: '过滤 + Top-N 排序',
  done: '完成',
}

export function ProgressIndicator({
  stage,
  progress,
  message,
  slow,
}: {
  stage: string
  progress: number
  message: string
  slow: boolean
}) {
  const pct = Math.round(progress * 100)
  return (
    <div className="border border-border rounded-md bg-chart p-5 space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{STAGE_LABELS[stage] ?? stage}</span>
        <span className="text-ink-soft numeric">{pct}%</span>
      </div>
      <div className="h-1.5 bg-surface rounded-sm overflow-hidden">
        <div className="h-full bg-accent transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-ink-soft">{message}</div>
      {slow && (
        <div className="text-xs text-warn border-t border-border pt-2 mt-2">
          任务运行较慢,如长时间无响应可改用 CLI:<code className="font-mono">uv run quant-select candidates …</code>
        </div>
      )}
    </div>
  )
}
