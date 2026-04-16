'use client'

import { useEffect, useMemo, useState } from 'react'
import { Badge, Button, PageHeader } from '@/components/ui'
import {
  fetchAgentCostSettings,
  updateAgentCostSettings,
  type AgentCostSettingsResponse,
} from '@/lib/observation-api'

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AgentCostSettingsResponse | null>(null)
  const [draftMax, setDraftMax] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const loadSettings = async () => {
      try {
        const response = await fetchAgentCostSettings()
        if (!active) return
        setSettings(response)
        setDraftMax((response.max_daily_cost ?? 0).toString())
      } catch {
        if (!active) return
        setError('Unable to load agent cost settings right now.')
      } finally {
        if (active) setLoading(false)
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

  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader title="Settings" subtitle="Agent execution budget controls">
        {budgetReached ? <Badge variant="red">Budget Reached</Badge> : <Badge variant="green">Budget Available</Badge>}
      </PageHeader>

      <div className="bg-bg-2 border border-border rounded-2xl p-6 max-w-2xl">
        <div className="text-[11px] text-[#4A5B7A] font-mono tracking-widest mb-2">DAILY COST LIMIT</div>
        <p className="text-[13px] text-[#8A9BBB] mb-5">
          When today&apos;s total incident cost reaches this value, agents stop executing new incidents and return an error.
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
    </div>
  )
}
