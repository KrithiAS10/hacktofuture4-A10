export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  const response = await fetch(url, { cache: 'no-store', ...init })
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}): ${url}`)
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
