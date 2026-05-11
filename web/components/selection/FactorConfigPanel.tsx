'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { useFactors, useDefaults } from '@/lib/queries'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/feedback/Skeleton'
import type { Factor, FactorConfig } from '@/lib/api-types'

export interface SelectionFormValues {
  as_of_date: string | null
  min_score: number
  top_n: number
  exclude_suspended: boolean
  exclude_st: boolean
  require_factors: string[]
  exclude_factors: string[]
  ma_short: number
  ma_long: number
  rsi_window: number
  rsi_threshold: number
  volume_window: number
  volume_multiplier: number
}

export function FactorConfigPanel({
  onSubmit,
  disabled,
}: {
  onSubmit: (values: SelectionFormValues) => void
  disabled?: boolean
}) {
  const factors = useFactors()
  const defaults = useDefaults()
  const [advanced, setAdvanced] = React.useState(false)

  const form = useForm<SelectionFormValues>({
    values: defaults.data
      ? {
          as_of_date: null,
          min_score: defaults.data.min_score,
          top_n: defaults.data.top_n,
          exclude_suspended: defaults.data.exclude_suspended,
          exclude_st: defaults.data.exclude_st,
          require_factors: defaults.data.require_factors ?? [],
          exclude_factors: defaults.data.exclude_factors ?? [],
          ma_short: defaults.data.ma_short,
          ma_long: defaults.data.ma_long,
          rsi_window: defaults.data.rsi_window,
          rsi_threshold: defaults.data.rsi_threshold,
          volume_window: defaults.data.volume_window,
          volume_multiplier: defaults.data.volume_multiplier,
        }
      : undefined,
  })

  if (factors.isLoading || defaults.isLoading) {
    return <div className="space-y-3 p-4"><Skeleton className="h-6 w-32" /><Skeleton className="h-32 w-full" /></div>
  }
  if (!factors.data || !defaults.data) return null

  const toggleArray = (key: 'require_factors' | 'exclude_factors', factor: string) => {
    const cur = form.getValues(key)
    const next = cur.includes(factor) ? cur.filter((f) => f !== factor) : [...cur, factor]
    form.setValue(key, next)
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5 p-4 text-sm">
      <Section title="截止日期">
        <input
          type="date"
          {...form.register('as_of_date')}
          className="h-8 px-2 rounded-sm border border-border bg-canvas text-sm w-full"
        />
        <div className="text-xs text-ink-muted mt-1">留空使用最近交易日</div>
      </Section>

      <Section title="启用因子">
        <div className="space-y-1.5">
          {factors.data.map((f: Factor) => (
            <div key={f.key} className="text-xs text-ink-soft">
              {f.name_cn}
              <span className="text-ink-muted ml-1 font-mono">({f.key})</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="排序">
        <Row label="min_score">
          <Input type="number" {...form.register('min_score', { valueAsNumber: true, min: 0, max: 6 })} className="w-20" />
        </Row>
        <Row label="top_n">
          <Input type="number" {...form.register('top_n', { valueAsNumber: true, min: 1 })} className="w-20" />
        </Row>
      </Section>

      <Section title="过滤">
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" {...form.register('exclude_suspended')} />排除停牌
        </label>
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" {...form.register('exclude_st')} />排除 ST
        </label>
        <div className="mt-2">
          <div className="text-xs text-ink-muted mb-1">必须命中的因子(require)</div>
          <div className="flex flex-wrap gap-1">
            {factors.data.map((f: Factor) => {
              const active = form.watch('require_factors').includes(f.key)
              return (
                <button type="button" key={f.key}
                  onClick={() => toggleArray('require_factors', f.key)}
                  className={'px-2 py-0.5 text-xs rounded-sm border ' +
                    (active ? 'border-accent bg-accent-soft' : 'border-border text-ink-muted')}>
                  {f.name_cn}
                </button>
              )
            })}
          </div>
        </div>
        <div className="mt-2">
          <div className="text-xs text-ink-muted mb-1">必须排除的因子(exclude)</div>
          <div className="flex flex-wrap gap-1">
            {factors.data.map((f: Factor) => {
              const active = form.watch('exclude_factors').includes(f.key)
              return (
                <button type="button" key={f.key}
                  onClick={() => toggleArray('exclude_factors', f.key)}
                  className={'px-2 py-0.5 text-xs rounded-sm border ' +
                    (active ? 'border-error bg-canvas text-error' : 'border-border text-ink-muted')}>
                  {f.name_cn}
                </button>
              )
            })}
          </div>
        </div>
      </Section>

      <button type="button" onClick={() => setAdvanced((v) => !v)} className="text-xs text-ink-soft hover:text-ink underline">
        {advanced ? '收起调参' : '展开调参'}
      </button>
      {advanced && (
        <Section title="调参(默认无需改)">
          <Row label="ma_short"><Input type="number" {...form.register('ma_short', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="ma_long"><Input type="number" {...form.register('ma_long', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="rsi_window"><Input type="number" {...form.register('rsi_window', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="rsi_threshold"><Input type="number" step="0.1" {...form.register('rsi_threshold', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="volume_window"><Input type="number" {...form.register('volume_window', { valueAsNumber: true })} className="w-20" /></Row>
          <Row label="volume_multiplier"><Input type="number" step="0.1" {...form.register('volume_multiplier', { valueAsNumber: true })} className="w-20" /></Row>
        </Section>
      )}

      <div className="flex gap-2 pt-2 border-t border-border">
        <Button type="submit" variant="primary" disabled={disabled} className="flex-1">开始选股 ▶</Button>
        <Button type="button" variant="ghost" onClick={() => form.reset()} disabled={disabled}>恢复默认</Button>
      </div>
    </form>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-xs uppercase tracking-wide text-ink-muted mb-1">{title}</legend>
      {children}
    </fieldset>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center justify-between gap-2 text-xs text-ink-soft">
      <span className="font-mono">{label}</span>
      {children}
    </label>
  )
}
