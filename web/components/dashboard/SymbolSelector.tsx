'use client'

import * as Popover from '@radix-ui/react-popover'
import * as React from 'react'
import { Input } from '@/components/ui/Input'
import { useSymbols } from '@/lib/queries'

export function SymbolSelector({
  value,
  onChange,
}: {
  value: string | null
  onChange: (symbol: string) => void
}) {
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState('')
  const [debounced, setDebounced] = React.useState('')

  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 300)
    return () => clearTimeout(t)
  }, [query])

  const { data, isLoading } = useSymbols(debounced || undefined)

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          className="h-8 px-2.5 text-sm rounded-sm bg-canvas border border-border min-w-[180px] text-left hover:border-border-strong"
          aria-label="选择标的"
        >
          {value ?? <span className="text-ink-muted">选择标的…</span>}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="bottom"
          align="start"
          sideOffset={4}
          className="z-50 w-[280px] rounded-md border border-border bg-chart shadow-md p-2"
        >
          <Input
            autoFocus
            placeholder="输入代码前缀,如 000001"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full mb-2"
          />
          <div className="max-h-[260px] overflow-y-auto">
            {isLoading && <div className="px-2 py-1.5 text-xs text-ink-muted">加载中…</div>}
            {!isLoading && data && data.length === 0 && (
              <div className="px-2 py-1.5 text-xs text-ink-muted">无匹配标的</div>
            )}
            {!isLoading && data?.map((row) => (
              <button
                key={row.symbol}
                onClick={() => { onChange(row.symbol); setOpen(false) }}
                className="w-full text-left px-2 py-1.5 text-sm rounded-sm hover:bg-accent-soft flex justify-between"
              >
                <span className="font-mono">{row.symbol}</span>
                <span className="text-xs text-ink-muted">{row.last_cached_date ?? '—'}</span>
              </button>
            ))}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
