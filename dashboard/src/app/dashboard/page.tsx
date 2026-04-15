'use client'
// src/app/dashboard/page.tsx
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, Server, Bot, CheckCircle } from 'lucide-react'
import { Badge, PageHeader, StatCard } from '@/components/ui'
import { SparklineChart } from '@/components/charts/SparklineChart'

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
}
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
}

const timeLabels = ['11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30','14:45','15:00','15:15','15:30']
const latencyData = [120, 125, 118, 130, 142, 155, 160, 142, 148, 139, 135, 142]

const recentEvents = [
  { severity: 'red' as const,   label: 'CRITICAL', service: 'payment-service', desc: 'High error rate detected (5.2% → 18.7%)',          time: '2m ago'  },
  { severity: 'amber' as const,  label: 'WARNING',  service: 'api-gateway',      desc: 'P95 latency spike (180ms → 450ms)',                 time: '14m ago' },
  { severity: 'green' as const,  label: 'RESOLVED', service: 'auth-service',      desc: 'Memory leak patched by Executor Agent',            time: '38m ago' },
  { severity: 'blue' as const,   label: 'INFO',     service: 'user-service',      desc: 'Auto-scaling triggered — added 4 replicas',        time: '52m ago' },
]

export default function DashboardPage() {
  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader title="Command Center" subtitle="Real-time cluster telemetry · Last sync: just now">
        <Badge variant="green">● HEALTHY</Badge>
        <Badge variant="blue" className="text-[10px]">Thu Apr 09 · 14:32 UTC</Badge>
      </PageHeader>

      {/* Stat Cards */}
      <motion.div
        variants={container} initial="hidden" animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"
      >
        <motion.div variants={item}>
          <StatCard
            label="Cluster Health"
            value="GOOD"
            sub="32/32 nodes responsive"
            valueColor="text-lerna-green"
            glow="blue"
            icon={<Activity size={18} className="text-lerna-green" />}
            iconBg="bg-[rgba(16,185,129,0.1)]"
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            label="Active Incidents"
            value="3"
            sub="1 critical · 2 warning"
            valueColor="text-lerna-red"
            icon={<AlertTriangle size={18} className="text-lerna-red" />}
            iconBg="bg-[rgba(239,68,68,0.1)]"
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            label="Services Running"
            value="147"
            sub="+3 since yesterday"
            valueColor="text-lerna-blue2"
            glow="blue"
            icon={<Server size={18} className="text-lerna-blue2" />}
            iconBg="bg-[rgba(59,130,246,0.1)]"
          />
        </motion.div>
        <motion.div variants={item}>
          <StatCard
            label="Agent Status"
            value="5/5"
            sub="All agents active"
            valueColor="text-lerna-purple2"
            glow="purple"
            icon={<Bot size={18} className="text-lerna-purple2" />}
            iconBg="bg-[rgba(168,85,247,0.1)]"
          />
        </motion.div>
      </motion.div>

      {/* Charts */}
      <motion.div
        variants={container} initial="hidden" animate="show"
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <motion.div variants={item} className="bg-bg-2 border border-border rounded-2xl p-5 hover:border-border-2 transition-colors">
          <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">CPU Usage</div>
          <div className="text-xl font-black text-lerna-blue2 mb-4">68.4%</div>
          <SparklineChart color="#3B82F6" gradientId="cpu" baseValue={65} height={100} showTooltip />
        </motion.div>

        <motion.div variants={item} className="bg-bg-2 border border-border rounded-2xl p-5 hover:border-border-2 transition-colors">
          <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">Memory Usage</div>
          <div className="text-xl font-black text-lerna-purple2 mb-4">74.1%</div>
          <SparklineChart color="#A855F7" gradientId="mem" baseValue={72} height={100} showTooltip />
        </motion.div>

        <motion.div variants={item} className="bg-bg-2 border border-border rounded-2xl p-5 hover:border-border-2 transition-colors">
          <div className="text-[11px] font-semibold text-[#8A9BBB] font-mono mb-1">Avg Latency</div>
          <div className="text-xl font-black text-lerna-cyan mb-4">142ms</div>
          <SparklineChart color="#06B6D4" gradientId="lat" data={latencyData} labels={timeLabels} height={100} showTooltip />
        </motion.div>
      </motion.div>

      {/* Recent Events */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.35 }}>
        <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
          Recent Events
        </div>
        <div className="flex flex-col gap-2">
          {recentEvents.map((e, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + i * 0.05 }}
              className="bg-bg-2 border border-border rounded-xl px-4 py-3 flex items-center gap-3 text-sm hover:border-border-2 transition-colors"
            >
              <Badge variant={e.severity} className="shrink-0">{e.label}</Badge>
              <span className="text-[#8A9BBB] shrink-0 font-mono text-xs">{e.service}</span>
              <span className="flex-1 text-[13px] text-[#E8EDF5]">{e.desc}</span>
              <span className="text-[11px] text-[#4A5B7A] font-mono shrink-0">{e.time}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}