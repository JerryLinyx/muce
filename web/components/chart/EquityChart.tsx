'use client'

import * as React from 'react'
import {
  createChart,
  LineSeries,
  AreaSeries,
  type Time,
} from 'lightweight-charts'

type EquityRow = Record<string, unknown>

export function EquityChart({ rows }: { rows: EquityRow[] }) {
  const containerRef = React.useRef<HTMLDivElement>(null)

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

    const equitySeries = chart.addSeries(LineSeries, { color: '#6b7c5e', lineWidth: 2 })
    equitySeries.setData(
      rows
        .map((r) => {
          const t = String(r.date).slice(0, 10) as Time
          const v = Number(r.equity)
          return Number.isFinite(v) ? { time: t, value: v } : null
        })
        .filter((v): v is { time: Time; value: number } => v !== null)
    )

    if (rows.length && rows[0] && 'drawdown' in rows[0]) {
      const dd = chart.addSeries(AreaSeries, {
        priceScaleId: 'left',
        topColor: 'rgba(193, 71, 71, 0.18)',
        bottomColor: 'rgba(193, 71, 71, 0.02)',
        lineColor: 'rgba(193, 71, 71, 0.6)',
        lineWidth: 1,
      })
      dd.setData(
        rows
          .map((r) => {
            const t = String(r.date).slice(0, 10) as Time
            const v = Number(r.drawdown)
            return Number.isFinite(v) ? { time: t, value: v } : null
          })
          .filter((v): v is { time: Time; value: number } => v !== null)
      )
      chart.priceScale('left').applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } })
    }

    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [rows])

  return <div ref={containerRef} className="chart-stage w-full" style={{ height: 360 }} />
}
