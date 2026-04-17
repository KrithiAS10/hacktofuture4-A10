'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { fetchAgentWorkflows, type AgentWorkflowResponse } from '@/lib/observation-api'

type WorkflowsContextValue = {
  workflows: AgentWorkflowResponse[]
  loading: boolean
  error: string | null
  /** Workflows not in terminal `completed` state (still open for triage). */
  openCount: number
  reload: () => Promise<void>
}

const WorkflowsContext = createContext<WorkflowsContextValue | null>(null)

const POLL_MS = 30_000

export function WorkflowsProvider({ children }: { children: ReactNode }) {
  const [workflows, setWorkflows] = useState<AgentWorkflowResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const res = await fetchAgentWorkflows(40)
      setWorkflows(res.workflows ?? [])
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load workflows')
      setWorkflows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
    const id = setInterval(() => void reload(), POLL_MS)
    return () => clearInterval(id)
  }, [reload])

  const openCount = useMemo(
    () => workflows.filter((w) => w.status !== 'completed').length,
    [workflows],
  )

  const value = useMemo(
    () => ({ workflows, loading, error, openCount, reload }),
    [workflows, loading, error, openCount, reload],
  )

  return <WorkflowsContext.Provider value={value}>{children}</WorkflowsContext.Provider>
}

export function useWorkflows(): WorkflowsContextValue {
  const ctx = useContext(WorkflowsContext)
  if (!ctx) {
    throw new Error('useWorkflows must be used within WorkflowsProvider')
  }
  return ctx
}
