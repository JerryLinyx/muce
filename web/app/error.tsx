'use client'

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-8">
      <h1 className="text-lg font-semibold mb-2">页面出错了</h1>
      <p className="text-sm text-ink-soft mb-4">{error.message || '未知错误'}</p>
      <button
        onClick={reset}
        className="px-3 py-1.5 text-sm rounded-sm bg-accent-soft text-ink hover:bg-accent hover:text-canvas transition-colors"
      >
        重试
      </button>
    </div>
  )
}
