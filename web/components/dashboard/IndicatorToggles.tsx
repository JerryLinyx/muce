'use client'

const OPTIONS = [
  { key: 'ma_20', label: 'MA 20' },
  { key: 'ma_60', label: 'MA 60' },
  { key: 'rsi_14', label: 'RSI 14' },
] as const

export function IndicatorToggles({
  value,
  onChange,
}: {
  value: string[]
  onChange: (next: string[]) => void
}) {
  const toggle = (key: string) => {
    onChange(value.includes(key) ? value.filter((k) => k !== key) : [...value, key])
  }
  return (
    <div className="inline-flex border border-border rounded-sm overflow-hidden">
      {OPTIONS.map((opt) => {
        const active = value.includes(opt.key)
        return (
          <button
            key={opt.key}
            onClick={() => toggle(opt.key)}
            className={
              'px-2.5 h-8 text-sm border-r border-border last:border-r-0 ' +
              (active ? 'bg-accent-soft text-ink' : 'text-ink-soft hover:bg-surface')
            }
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
