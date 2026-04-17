'use client'

import type { ReactNode } from 'react'
import { WorkflowsProvider } from '@/context/WorkflowsContext'

export function AppProviders({ children }: { children: ReactNode }) {
  return <WorkflowsProvider>{children}</WorkflowsProvider>
}
