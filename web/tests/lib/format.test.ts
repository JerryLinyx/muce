import { describe, it, expect } from 'vitest'
import { fmtPercent, fmtNumber, fmtDate, fmtCompactNumber } from '@/lib/format'

describe('fmtPercent', () => {
  it('renders + sign for positives, 2 decimals', () => {
    expect(fmtPercent(0.1234)).toBe('+12.34%')
    expect(fmtPercent(-0.05)).toBe('-5.00%')
    expect(fmtPercent(0)).toBe('+0.00%')
  })
  it('handles null/undefined', () => {
    expect(fmtPercent(null)).toBe('—')
    expect(fmtPercent(undefined)).toBe('—')
  })
})

describe('fmtNumber', () => {
  it('thousands separators', () => {
    expect(fmtNumber(1234567.89)).toBe('1,234,567.89')
  })
  it('respects decimals', () => {
    expect(fmtNumber(1.234, 1)).toBe('1.2')
  })
  it('handles null', () => {
    expect(fmtNumber(null)).toBe('—')
  })
})

describe('fmtDate', () => {
  it('formats ISO date as YYYY-MM-DD', () => {
    expect(fmtDate('2026-05-11T08:30:00Z')).toBe('2026-05-11')
    expect(fmtDate('2026-05-11')).toBe('2026-05-11')
  })
})

describe('fmtCompactNumber', () => {
  it('uses 万 / 亿 for Chinese magnitudes', () => {
    expect(fmtCompactNumber(12345)).toBe('1.23万')
    expect(fmtCompactNumber(123_456_789)).toBe('1.23亿')
    expect(fmtCompactNumber(999)).toBe('999')
  })
})
