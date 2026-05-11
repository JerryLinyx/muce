'use client'

export default function PageError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="p-8">
      <h2 className="text-md font-medium mb-2">页面出错了</h2>
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
