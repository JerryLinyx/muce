'use client'

import * as Collapsible from '@radix-ui/react-collapsible'
import { useState } from 'react'

export function MetaPanel({ manifest }: { manifest: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <Collapsible.Trigger className="text-sm text-ink-soft hover:text-ink underline">
        {open ? '隐藏' : '显示'}元信息
      </Collapsible.Trigger>
      <Collapsible.Content className="mt-2">
        <div className="border border-border rounded-md bg-chart p-3">
          <table className="w-full text-xs">
            <tbody>
              {['run_id', 'kind', 'created_at', 'elapsed_seconds', 'git_commit', 'git_dirty'].map((key) => (
                <tr key={key}>
                  <td className="text-ink-muted py-0.5 pr-3 align-top">{key}</td>
                  <td className="font-mono py-0.5">{String(manifest[key] ?? '—')}</td>
                </tr>
              ))}
              <tr>
                <td className="text-ink-muted py-0.5 pr-3 align-top">data_range</td>
                <td className="font-mono py-0.5">{JSON.stringify(manifest.data_range ?? null)}</td>
              </tr>
              <tr>
                <td className="text-ink-muted py-0.5 pr-3 align-top">symbols</td>
                <td className="font-mono py-0.5">{Array.isArray(manifest.symbols) ? manifest.symbols.join(', ') : '—'}</td>
              </tr>
            </tbody>
          </table>
          <details className="mt-2">
            <summary className="text-xs text-ink-muted cursor-pointer">完整 manifest JSON</summary>
            <pre className="text-xs mt-2 max-h-[280px] overflow-auto bg-canvas p-2 rounded-sm border border-border">
              {JSON.stringify(manifest, null, 2)}
            </pre>
          </details>
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  )
}
