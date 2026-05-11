'use client'

import * as React from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type Time,
} from 'lightweight-charts'
import type { BarRow } from '@/lib/api-types'

interface Props {
  rows: BarRow[]
  indicators: string[]
}

export function KLineChart({ rows, indicators }: Props) {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<IChartApi | null>(null)

  React.useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: '#fbfaf6' },
        textColor: '#5c5c56',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      grid: {
        vertLines: { color: 'rgba(26, 26, 20, 0.06)' },
        horzLines: { color: 'rgba(26, 26, 20, 0.06)' },
      },
      timeScale: { borderColor: 'rgba(26, 26, 20, 0.16)' },
      rightPriceScale: { borderColor: 'rgba(26, 26, 20, 0.16)' },
      crosshair: { mode: 1 },
    })
    chartRef.current = chart

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#c14747',
      downColor: '#4a7d52',
      borderUpColor: '#c14747',
      borderDownColor: '#4a7d52',
      wickUpColor: '#c14747',
      wickDownColor: '#4a7d52',
    })
    candle.setData(
      rows.map((r) => ({
        time: r.date as Time,
        open: r.open as number,
        high: r.high as number,
        low: r.low as number,
        close: r.close as number,
      }))
    )

    const volSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      color: 'rgba(107, 124, 94, 0.5)',
    })
    volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } })
    volSeries.setData(rows.map((r) => ({
      time: r.date as Time,
      value: (r.volume as number) ?? 0,
      color: (r.close as number) >= (r.open as number)
        ? 'rgba(193, 71, 71, 0.4)'
        : 'rgba(74, 125, 82, 0.4)',
    })))

    for (const ind of indicators) {
      if (!ind.startsWith('ma_')) continue
      const values = rows
        .map((r) => {
          const v = (r as Record<string, unknown>)[ind]
          return typeof v === 'number' && Number.isFinite(v) ? { time: r.date as Time, value: v } : null
        })
        .filter((v): v is { time: Time; value: number } => v !== null)
      if (values.length === 0) continue
      const line = chart.addSeries(LineSeries, {
        color: ind === 'ma_20' ? '#6b7c5e' : '#c08a3a',
        lineWidth: 1,
      })
      line.setData(values)
    }

    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [rows, indicators])

  return <div ref={containerRef} className="chart-stage w-full h-full" />
}
