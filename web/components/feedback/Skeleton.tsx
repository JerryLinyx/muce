export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={'animate-pulse bg-surface rounded-sm ' + className} />
}
