'use client'

import { useHealth } from '@/lib/queries'

export function HealthBadge() {
  const { data, isError, isLoading } = useHealth()
  let label = '检查中…'
  let cls = 'text-ink-muted'
  if (isError) { label = '后端离线'; cls = 'text-error' }
  else if (data?.status === 'ok') { label = '后端在线'; cls = 'text-down' }
  return <span className={`text-xs ${cls}`} aria-live="polite">{!isLoading && label}</span>
}
