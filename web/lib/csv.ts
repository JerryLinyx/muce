export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (rows.length === 0) return
  const first = rows[0]!
  const headers = Object.keys(first)
  const escape = (v: unknown): string => {
    if (v == null) return ''
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const body = rows.map((r) => headers.map((h) => escape(r[h])).join(',')).join('\n')
  const csv = '﻿' + headers.join(',') + '\n' + body  // BOM for Excel zh-CN
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
