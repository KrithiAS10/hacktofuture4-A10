'use client'

import { useEffect, useMemo, useState } from 'react'
import { Badge, Button, PageHeader } from '@/components/ui'
import {
  fetchAgentCostSettings,
  fetchAgentExecutionMode,
  updateAgentCostSettings,
  updateAgentExecutionMode,
  type AgentCostSettingsResponse,
  type AgentExecutionMode,
} from '@/lib/observation-api'

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
}

const RESPONSE_MODES: {
  value: AgentExecutionMode
  title: string
  description: string
}[] = [
  {
    value: 'autonomous',
    title: 'Autonomous',
    description:
      'When detection finds an incident, it starts a workflow and the executor may run mutating Kubernetes actions (scale, rollout, patches) when the model chooses them.',
  },
  {
    value: 'advisory',
    title: 'Advisory',
    description:
      'Workflows still run from detection, but the executor only uses dry-run validation and written operator steps — no live apply, scale, or destructive cluster changes from tools.',
  },
  {
    value: 'paused',
    title: 'Manual only',
    description:
      'Detection keeps evaluating signals but does not start workflows automatically. You can still start runs from the agents UI, chat, or API.',
  },
]

export default function SettingsPage() {
  const [settings, setSettings] = useState<AgentCostSettingsResponse | null>(null)
  const [draftMax, setDraftMax] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [executionMode, setExecutionMode] = useState<AgentExecutionMode>('autonomous')
  const [modeLoading, setModeLoading] = useState(true)
  const [modeSaving, setModeSaving] = useState(false)
  const [modeError, setModeError] = useState<string | null>(null)
  const [modeNotice, setModeNotice] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const loadSettings = async () => {
      try {
        const [costResponse, modeResponse] = await Promise.all([
          fetchAgentCostSettings(),
          fetchAgentExecutionMode(),
        ])
        if (!active) return
        setSettings(costResponse)
        setDraftMax((costResponse.max_daily_cost ?? 0).toString())
        setExecutionMode(modeResponse.mode)
      } catch {
        if (!active) return
        setError('Unable to load agent cost settings right now.')
        try {
          const modeResponse = await fetchAgentExecutionMode()
          if (active) setExecutionMode(modeResponse.mode)
        } catch {
          if (active) setModeError('Unable to load response mode.')
        }
      } finally {
        if (active) {
          setLoading(false)
          setModeLoading(false)
        }
      }
    }
    void loadSettings()
    return () => {
      active = false
    }
  }, [])

  const parsedDraft = Number(draftMax)
  const canSave = !saving && Number.isFinite(parsedDraft) && parsedDraft >= 0
  const budgetReached = useMemo(() => {
    if (!settings || settings.max_daily_cost == null) return false
    return settings.spent_today >= settings.max_daily_cost
  }, [settings])

  const onSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const updated = await updateAgentCostSettings(parsedDraft)
      setSettings(updated)
      setDraftMax((updated.max_daily_cost ?? parsedDraft).toString())
      setNotice('Daily max cost updated successfully.')
    } catch {
      setError('Failed to update daily max cost.')
    } finally {
      setSaving(false)
    }
  }

  const onSaveMode = async (next: AgentExecutionMode) => {
    setModeSaving(true)
    setModeError(null)
    setModeNotice(null)
    try {
      const res = await updateAgentExecutionMode(next)
      setExecutionMode(res.mode)
      setModeNotice('Response mode updated.')
    } catch {
      setModeError('Failed to update response mode.')
    } finally {
      setModeSaving(false)
    }
  }

  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader title="Settings" subtitle="Agent budget and how workflows react to detected incidents">
        {budgetReached ? <Badge variant="red">Budget Reached</Badge> : <Badge variant="green">Budget Available</Badge>}
      </PageHeader>

      <div className="bg-bg-2 border border-border rounded-2xl p-6 max-w-2xl">
        <div className="text-[11px] text-[#4A5B7A] font-mono tracking-widest mb-2">DAILY COST LIMIT</div>
        <p className="text-[13px] text-[#8A9BBB] mb-5">
          Daily cap is stored in the observation backend database and synced to the agents service for enforcement. If no
          saved value exists yet, the server uses <span className="text-[#E8EDF5]">LERNA_DEFAULT_MAX_DAILY_AGENT_COST_USD</span>{' '}
          (default 100). When today&apos;s measured API spend reaches the cap, new incidents are rejected.
        </p>

        {loading ? (
          <div className="text-sm text-[#8A9BBB]">Loading settings...</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
              <div className="bg-bg-3 border border-border rounded-lg p-3">
                <div className="text-[#4A5B7A] text-xs font-mono mb-1">Spent Today</div>
                <div className="text-white font-semibold">{formatCurrency(settings?.spent_today ?? 0)}</div>
              </div>
              <div className="bg-bg-3 border border-border rounded-lg p-3">
                <div className="text-[#4A5B7A] text-xs font-mono mb-1">Max Daily Cost</div>
                <div className="text-white font-semibold">
                  {settings?.max_daily_cost == null ? 'Not set' : formatCurrency(settings.max_daily_cost)}
                </div>
              </div>
              <div className="bg-bg-3 border border-border rounded-lg p-3">
                <div className="text-[#4A5B7A] text-xs font-mono mb-1">Remaining</div>
                <div className={budgetReached ? 'text-lerna-red font-semibold' : 'text-white font-semibold'}>
                  {settings?.remaining_today == null ? 'Unlimited' : formatCurrency(settings.remaining_today)}
                </div>
              </div>
            </div>

            <label className="block">
              <span className="text-sm text-[#8A9BBB]">Set max daily cost (USD)</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={draftMax}
                onChange={(event) => setDraftMax(event.target.value)}
                className="mt-2 w-full bg-bg-3 border border-border-2 rounded-xl p-3 text-sm text-[#E8EDF5] outline-none focus:border-lerna-blue"
              />
            </label>

            <div className="flex items-center gap-3">
              <Button variant="primary" onClick={onSave} disabled={!canSave}>
                {saving ? 'Saving...' : 'Save daily max'}
              </Button>
              {notice && <span className="text-sm text-lerna-green">{notice}</span>}
              {error && <span className="text-sm text-lerna-red">{error}</span>}
            </div>
          </div>
        )}
      </div>

      <div className="bg-bg-2 border border-border rounded-2xl p-6 max-w-2xl">
        <div className="text-[11px] text-[#4A5B7A] font-mono tracking-widest mb-2">INCIDENT RESPONSE MODE</div>
        <p className="text-[13px] text-[#8A9BBB] mb-5">
          Stored in the observation backend database and synced to the agents service and shared Redis so detection and
          LangGraph runs stay aligned. Advisory tool restrictions apply to the multi-agent (LangGraph) executor; the
          legacy single-agent engine is not tool-gated the same way.
        </p>

        {modeLoading ? (
          <div className="text-sm text-[#8A9BBB]">Loading mode…</div>
        ) : (
          <div className="space-y-3">
            {RESPONSE_MODES.map((opt) => {
              const selected = executionMode === opt.value
              return (
                <label
                  key={opt.value}
                  className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition-colors ${
                    selected ? 'border-lerna-blue bg-bg-3' : 'border-border bg-bg-3/40 hover:border-border-2'
                  }`}
                >
                  <input
                    type="radio"
                    name="execution-mode"
                    className="mt-1"
                    checked={selected}
                    disabled={modeSaving}
                    onChange={() => void onSaveMode(opt.value)}
                  />
                  <div>
                    <div className="text-sm font-semibold text-white">{opt.title}</div>
                    <p className="text-[12px] text-[#8A9BBB] mt-1 leading-relaxed">{opt.description}</p>
                  </div>
                </label>
              )
            })}
            {modeNotice ? <span className="text-sm text-lerna-green block pt-1">{modeNotice}</span> : null}
            {modeError ? <span className="text-sm text-lerna-red block pt-1">{modeError}</span> : null}
          </div>
        )}
      </div>
    </div>
  )
}
