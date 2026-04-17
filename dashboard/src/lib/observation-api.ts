export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  const response = await fetch(url, { cache: 'no-store', ...init })
  if (!response.ok) {
    let detail: string | undefined
    try {
      const body = await response.json()
      if (body && typeof body === 'object') {
        // FastAPI-style errors typically use `detail`
        detail = (body as any).detail || (body as any).message
      }
    } catch {
      // Non-JSON error responses
    }

    const error = new Error(
      `Request failed (${response.status}): ${url}${detail ? ` - ${detail}` : ''}`,
    ) as Error & {
      status?: number
    }
    error.status = response.status
    throw error
  }
  return (await response.json()) as T
}

export interface ClusterHealthResponse {
  ok: boolean
  score_hint?: number
  nodes?: { total?: number; ready?: number; not_ready?: string[] }
  deployments?: { total?: number; degraded_count?: number }
  services?: { total?: number; without_ready_endpoints_count?: number }
  last_updated?: string
  reason?: string
}

export interface ClusterSummaryResponse {
  available: boolean
  last_updated?: string
  reason?: string
  namespace_scope?: string | null
  nodes?: { total?: number; ready?: number; not_ready?: string[] }
  deployments?: {
    total?: number
    degraded_count?: number
    degraded?: Array<{ namespace: string; name: string; ready: number; desired: number }>
  }
  services?: {
    total?: number
    without_ready_endpoints_count?: number
    without_ready_endpoints?: Array<{ namespace: string; name: string; type?: string }>
  }
  pods?: {
    total?: number
    non_running_count?: number
    restarting_count?: number
    non_running?: Array<{ namespace: string; name: string; phase: string }>
    top_restarting?: Array<{ namespace: string; name: string; restarts: number; reason?: string | null }>
  }
    recent_events?: Array<{
      type?: string
      reason?: string
      namespace?: string
      object?: string
      message?: string
      count?: number
      last_timestamp?: string
    }>
    metrics?: {
      cpu_percentage: number | null
      memory_percentage: number | null
      cpu_available?: boolean
      memory_available?: boolean
      cpu_query?: string | null
      memory_query?: string | null
      cpu_reason?: string | null
      memory_reason?: string | null
    }
  }

export interface LokiQueryResponse {
  data?: {
    result?: Array<{
      stream?: Record<string, string>
      values?: Array<[string, string]>
    }>
  }
}

export interface AgentPromptEntry {
  agent_id: string
  prompt: string
}

export interface AgentPromptsResponse {
  prompts: AgentPromptEntry[]
}

export interface AgentPromptResetResponse {
  agent_id: string
  reset: boolean
}

export interface AgentWorkflowResponse {
  workflow_id: string
  incident_id: string
  cost?: number | null
  status: string
  accepted_at: string
  current_stage?: string | null
  started_at?: string | null
  finished_at?: string | null
  // Runtime stores may set this to a stringified exception message.
  result?: Record<string, unknown> | string | null
  api_cost_usd?: number | null
  api_usage?: Record<string, unknown> | null
  incident_report?: Record<string, unknown> | null
}

/** UI chat message (local state + optional persistence). */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface AgentWorkflowListResponse {
  workflows: AgentWorkflowResponse[]
}

export interface AgentChatResponse {
  message: string
  workflow_id?: string
}

export interface AgentChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AgentCostSettingsResponse {
  max_daily_cost?: number | null
  spent_today: number
  remaining_today?: number | null
}

export type AgentExecutionMode = 'autonomous' | 'advisory' | 'paused'

export interface AgentExecutionModeResponse {
  mode: AgentExecutionMode
}

export async function fetchClusterHealth() {
  return request<ClusterHealthResponse>('/cluster/health')
}

export async function fetchClusterSummary() {
  return request<ClusterSummaryResponse>('/cluster/summary')
}

export async function fetchRecentLogs(limit = 100) {
  const query = encodeURIComponent('{}')
  return request<LokiQueryResponse>(`/obs/logs?query=${query}&limit=${limit}`)
}

export async function fetchAgentPrompts(agentIds?: string[]) {
  const idsQuery = agentIds && agentIds.length > 0 ? `?ids=${encodeURIComponent(agentIds.join(','))}` : ''
  return request<AgentPromptsResponse>(`/agents/prompts${idsQuery}`)
}

export async function updateAgentPrompt(agentId: string, prompt: string) {
  return request<AgentPromptEntry>(`/agents/prompts/${encodeURIComponent(agentId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
}

export async function resetAgentPrompt(agentId: string) {
  return request<AgentPromptResetResponse>(`/agents/prompts/${encodeURIComponent(agentId)}`, {
    method: 'DELETE',
  })
}

export async function fetchLatestAgentWorkflow() {
  return request<AgentWorkflowResponse>(`/agents/workflows/latest`)
}

export async function fetchAgentWorkflows(limit = 25) {
  return request<AgentWorkflowListResponse>(`/agents/workflows?limit=${limit}`)
}

export async function fetchAgentWorkflow(workflowId: string) {
  return request<AgentWorkflowResponse>(`/agents/workflows/${encodeURIComponent(workflowId)}`)
}

export async function chatWithOrchestrator(
  message: string,
  workflowId?: string,
  incidentId?: string,
  messages?: AgentChatMessage[],
) {
  return request<AgentChatResponse>(`/agents/orchestrator/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, workflow_id: workflowId, incident_id: incidentId, messages }),
  })
}

export async function fetchAgentCostSettings() {
  return request<AgentCostSettingsResponse>('/agents/cost-settings')
}

export async function updateAgentCostSettings(maxDailyCost: number) {
  return request<AgentCostSettingsResponse>('/agents/cost-settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max_daily_cost: maxDailyCost }),
  })
}

export async function fetchAgentExecutionMode() {
  return request<AgentExecutionModeResponse>('/agents/execution-mode')
}

export async function updateAgentExecutionMode(mode: AgentExecutionMode) {
  return request<AgentExecutionModeResponse>('/agents/execution-mode', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  })
}
