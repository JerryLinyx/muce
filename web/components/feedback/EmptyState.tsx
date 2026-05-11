export function EmptyState({ title, hint }: { title: string; hint?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-md font-medium text-ink-soft">{title}</div>
      {hint && <div className="text-sm text-ink-muted mt-2 max-w-md">{hint}</div>}
    </div>
  )
}
