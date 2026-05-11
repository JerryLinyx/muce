import { Skeleton } from './Skeleton'

export function TableSkeleton({ rows = 8, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-border rounded-md overflow-hidden">
      <div className="bg-surface flex">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="flex-1 p-2"><Skeleton className="h-3" /></div>
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex border-t border-border">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="flex-1 p-2"><Skeleton className="h-3" /></div>
          ))}
        </div>
      ))}
    </div>
  )
}
