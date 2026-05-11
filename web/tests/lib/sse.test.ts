import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSelectionJobStream } from '@/lib/sse'

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  listeners: Record<string, ((e: { data: string }) => void)[]> = {}
  onerror: (() => void) | null = null
  closed = false
  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }
  addEventListener(event: string, cb: (e: { data: string }) => void) {
    this.listeners[event] = this.listeners[event] ?? []
    this.listeners[event].push(cb)
  }
  removeEventListener() {}
  close() { this.closed = true }
  emit(event: string, data: unknown) {
    for (const cb of this.listeners[event] ?? []) cb({ data: JSON.stringify(data) })
  }
}

beforeEach(() => {
  MockEventSource.instances = []
  ;(globalThis as unknown as { EventSource: typeof MockEventSource }).EventSource = MockEventSource
})

describe('useSelectionJobStream', () => {
  it('starts in idle when jobId is null', () => {
    const { result } = renderHook(() => useSelectionJobStream(null))
    expect(result.current.status).toBe('idle')
  })

  it('transitions through running -> done', () => {
    const { result } = renderHook(() => useSelectionJobStream('JOB1'))
    expect(result.current.status).toBe('running')
    const es = MockEventSource.instances[0]!
    act(() => es.emit('progress', { stage: 'load_panel', progress: 0.1, message: '加载...' }))
    expect(result.current).toMatchObject({ status: 'running', stage: 'load_panel', progress: 0.1 })
    act(() => es.emit('done', { stage: 'done', progress: 1, result: { candidates: [], summary: {} } }))
    expect(result.current.status).toBe('done')
    expect(es.closed).toBe(true)
  })

  it('handles failed event', () => {
    const { result } = renderHook(() => useSelectionJobStream('JOB2'))
    const es = MockEventSource.instances[0]!
    act(() => es.emit('failed', { error: 'boom' }))
    expect(result.current).toMatchObject({ status: 'failed', error: 'boom' })
    expect(es.closed).toBe(true)
  })

  it('closes when jobId changes or unmounts', () => {
    const { rerender, unmount } = renderHook(({ id }: { id: string }) => useSelectionJobStream(id), { initialProps: { id: 'A' } })
    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0]!.closed).toBe(false)
    rerender({ id: 'B' })
    expect(MockEventSource.instances[0]!.closed).toBe(true)
    expect(MockEventSource.instances).toHaveLength(2)
    unmount()
    expect(MockEventSource.instances[1]!.closed).toBe(true)
  })
})
