'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { HealthBadge } from '@/components/feedback/HealthBadge'

const TABS = [
  { href: '/dashboard', label: '看板' },
  { href: '/selection', label: '选股' },
  { href: '/reports', label: '报告' },
] as const

export function TopBar() {
  const pathname = usePathname()
  return (
    <header
      className="flex items-center justify-between border-b border-border bg-canvas px-5"
      style={{ height: 44 }}
    >
      <div className="flex items-center gap-6">
        <Link href="/dashboard" className="text-md font-semibold tracking-tight">
          Muce <span className="text-ink-muted text-sm">牧策</span>
        </Link>
        <nav className="flex items-center gap-1">
          {TABS.map((tab) => {
            const active = pathname?.startsWith(tab.href)
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={
                  'px-3 py-1.5 text-sm rounded-sm transition-colors ' +
                  (active
                    ? 'bg-accent-soft text-ink'
                    : 'text-ink-soft hover:text-ink hover:bg-surface')
                }
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>
      </div>
      <HealthBadge />
    </header>
  )
}
