'use client'
// src/app/agents/page.tsx
import { motion } from 'framer-motion'
import { Badge, PageHeader } from '@/components/ui'
import { agents, type Agent } from '@/lib/mock-data'
import clsx from 'clsx'

const statusConfig: Record<Agent['status'], { label: string; dotClass: string; textColor: string }> = {
  running:    { label: 'Running',    dotClass: 'bg-lerna-green pulse-green',   textColor: 'text-lerna-green'   },
  processing: { label: 'Processing', dotClass: 'bg-lerna-amber pulse-amber',   textColor: 'text-lerna-amber'   },
  idle:       { label: 'Idle',       dotClass: 'bg-[#4A5B7A]',                 textColor: 'text-[#4A5B7A]'     },
  monitoring: { label: 'Monitoring', dotClass: 'bg-lerna-cyan pulse-blue',     textColor: 'text-lerna-cyan'    },
}

const progressGradient: Record<string, string> = {
  filter:     'from-lerna-green to-emerald-400',
  diagnosis:  'from-lerna-amber to-orange-400',
  planning:   'from-lerna-purple to-lerna-purple2',
  executor:   'from-lerna-blue to-lerna-cyan',
  validation: 'from-lerna-cyan to-lerna-green',
}

const pipelineSteps = [
  { id: 'filter',     label: 'Filter',   color: 'rgba(16,185,129,0.15)',  text: 'text-lerna-green',   border: 'rgba(16,185,129,0.2)'  },
  { id: 'diagnosis',  label: 'Diagnose', color: 'rgba(245,158,11,0.15)',  text: 'text-lerna-amber',   border: 'rgba(245,158,11,0.2)'  },
  { id: 'planning',   label: 'Plan',     color: 'rgba(168,85,247,0.15)', text: 'text-lerna-purple2', border: 'rgba(168,85,247,0.2)' },
  { id: 'executor',   label: 'Execute',  color: 'rgba(59,130,246,0.15)',  text: 'text-lerna-blue2',   border: 'rgba(59,130,246,0.2)'  },
  { id: 'validation', label: 'Validate', color: 'rgba(6,182,212,0.15)',   text: 'text-lerna-cyan',    border: 'rgba(6,182,212,0.2)'   },
]

export default function AgentsPage() {
  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader title="Autonomous Agents" subtitle="Multi-agent remediation pipeline · 5/5 active">
        <Badge variant="green">● 5/5 RUNNING</Badge>
      </PageHeader>

      {/* Pipeline banner */}
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        className="bg-gradient-to-r from-[rgba(59,130,246,0.06)] to-[rgba(168,85,247,0.06)] border border-border rounded-2xl px-5 py-4 flex items-center justify-between gap-4 flex-wrap"
      >
        <div>
          <div className="text-[10px] text-[#4A5B7A] font-mono tracking-widest mb-2">PIPELINE STATUS</div>
          <div className="flex items-center gap-0 flex-wrap">
            {pipelineSteps.map((step, i) => (
              <div key={step.id} className="flex items-center">
                <span
                  className={clsx('text-[12px] px-3 py-1.5 border font-mono font-semibold', step.text)}
                  style={{
                    background: step.color,
                    borderColor: step.border,
                    borderRadius: i === 0 ? '6px 0 0 6px' : i === pipelineSteps.length - 1 ? '0 6px 6px 0' : '0',
                  }}
                >
                  {step.label}
                </span>
                {i < pipelineSteps.length - 1 && (
                  <span className="text-[10px] text-[#4A5B7A] px-1.5">→</span>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="text-[13px] text-[#8A9BBB]">
          Processing <strong className="text-white">INC-2024-0891</strong>
        </div>
      </motion.div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map((agent, i) => {
          const status = statusConfig[agent.status]
          const isActive = agent.status === 'processing'

          return (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, duration: 0.35 }}
              whileHover={{ y: -2 }}
              className={clsx(
                'bg-bg-2 border rounded-2xl p-6 transition-all duration-200',
                isActive ? 'border-[rgba(59,130,246,0.4)]' : 'border-border hover:border-border-2'
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center text-xl"
                  style={{ background: agent.bgColor }}
                >
                  {agent.emoji}
                </div>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span className={clsx('w-2 h-2 rounded-full shrink-0', status.dotClass)} />
                  <span className={status.textColor}>{status.label}</span>
                </div>
              </div>

              {/* Name */}
              <div className="font-bold text-[15px] mb-0.5">{agent.name}</div>
              <div className="text-[11px] text-[#4A5B7A] font-mono mb-4">{agent.role}</div>

              {/* Info rows */}
              <div className="space-y-0">
                <div className="flex justify-between py-2 border-b border-white/[0.04] text-[12px]">
                  <span className="text-[#4A5B7A]">Current Task</span>
                  <span className="font-mono text-[11px] text-right">{agent.currentTask}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-white/[0.04] text-[12px]">
                  <span className="text-[#4A5B7A]">Last Action</span>
                  <span className="text-[11px] text-right" style={{ color: agent.accentColor }}>{agent.lastAction}</span>
                </div>
                <div className="flex justify-between py-2 text-[12px]">
                  <span className="text-[#4A5B7A]">{agent.metricLabel}</span>
                  <span className="font-mono text-[11px]">{agent.metric}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-4 h-[3px] bg-bg-4 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${agent.progress}%` }}
                  transition={{ delay: i * 0.08 + 0.3, duration: 0.6, ease: 'easeOut' }}
                  className={clsx('h-full rounded-full bg-gradient-to-r', progressGradient[agent.id])}
                />
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}