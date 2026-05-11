import { describe, it, expect } from 'vitest'
import { paramsFromSearch, mergeSearch } from '@/lib/url-state'

describe('paramsFromSearch', () => {
  it('returns flat record', () => {
    const sp = new URLSearchParams('symbol=000001.SZ&adjust=qfq&indicators=ma_20,rsi_14')
    expect(paramsFromSearch(sp)).toEqual({
      symbol: '000001.SZ', adjust: 'qfq', indicators: 'ma_20,rsi_14',
    })
  })
})

describe('mergeSearch', () => {
  it('overrides specified keys, preserves others', () => {
    const sp = new URLSearchParams('a=1&b=2')
    expect(mergeSearch(sp, { b: '20', c: '30' })).toBe('a=1&b=20&c=30')
  })
  it('drops keys set to null/empty', () => {
    const sp = new URLSearchParams('a=1&b=2')
    expect(mergeSearch(sp, { a: null, b: '' })).toBe('')
  })
})
