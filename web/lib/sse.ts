'use client'

import { useEffect, useState } from 'react'
import type { SelectionResult } from './api-types'

export type JobUIState =
  | { status: 'idle' }
  | { status: 'running'; stage: string; progress: number; message: string }
  | { status: 'done'; result: SelectionResult }
  | { status: 'failed'; error: string }

export function useSelectionJobStream(jobId: string | null): JobUIState {
  const [state, setState] = useState<JobUIState>({ status: 'idle' })

  useEffect(() => {
    if (!jobId) {
      setState({ status: 'idle' })
      return
    }
    setState({ status: 'running', stage: 'pending', progress: 0, message: '提交中...' })

    const es = new EventSource(`/api/selection/jobs/${jobId}/stream`)

    es.addEventListener('progress', (e) => {
      const p = JSON.parse((e as MessageEvent).data) as { stage: string; progress: number; message: string }
      setState({ status: 'running', stage: p.stage, progress: p.progress, message: p.message })
    })
    es.addEventListener('done', (e) => {
      const p = JSON.parse((e as MessageEvent).data) as { result: SelectionResult }
      setState({ status: 'done', result: p.result })
      es.close()
    })
    es.addEventListener('failed', (e) => {
      const p = JSON.parse((e as MessageEvent).data) as { error: string }
      setState({ status: 'failed', error: p.error })
      es.close()
    })

    return () => es.close()
  }, [jobId])

  return state
}
