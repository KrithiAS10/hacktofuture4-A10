'use client'
// src/app/incidents/page.tsx
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { Badge, Button, PageHeader } from '@/components/ui'
import { incidents, type Incident } from '@/lib/mock-data'
import clsx from 'clsx'

const severityBorder: Record<Incident['severity'], string> = {
  critical: 'before:bg-lerna-red before:shadow-[0_0_8px_#EF4444]',
  warning:  'before:bg-lerna-amber',
  info:     'before:bg-lerna-blue',
}

const statusBadge: Record<Incident['status'], { variant: 'red' | 'amber' | 'blue' | 'green'; label: string }> = {
  active:        { variant: 'red',   label: 'ACTIVE' },
  investigating: { variant: 'amber', label: 'INVESTIGATING' },
  monitoring:    { variant: 'blue',  label: 'MONITORING' },
  resolved:      { variant: 'green', label: 'RESOLVED' },
}

const priorityColor: Record<Incident['priority'], string> = {
  P1: 'bg-[rgba(239,68,68,0.2)] text-[#FF6B6B]',
  P2: 'bg-[rgba(245,158,11,0.2)] text-[#FFC14D]',
  P3: 'bg-[rgba(59,130,246,0.2)] text-lerna-blue2',
}

export default function IncidentsPage() {
  return (
    <div className="p-7 flex flex-col gap-6">
      <PageHeader title="Incidents" subtitle="Active · Investigating · Resolved">
        <Badge variant="red">3 Active</Badge>
        <Button variant="outline">Filter</Button>
      </PageHeader>

      <div className="flex flex-col gap-3">
        {incidents.map((inc, i) => {
          const status = statusBadge[inc.status]
          const isResolved = inc.status === 'resolved'

          return (
            <motion.div
              key={inc.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.07, duration: 0.3 }}
            >
              <Link href={`/incidents/${inc.id}`}>
                <div className={clsx(
                  'relative bg-bg-2 border border-border rounded-2xl px-6 py-5',
                  'flex items-center gap-5 cursor-pointer transition-all duration-200',
                  'hover:border-border-2 hover:bg-bg-3 hover:translate-x-1',
                  'before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[3px] before:rounded-l-2xl',
                  severityBorder[inc.severity],
                  isResolved && 'opacity-60'
                )}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 mb-2 flex-wrap">
                      <span className={clsx('px-2.5 py-1 rounded-full text-[10px] font-bold font-mono tracking-wide', priorityColor[inc.priority])}>
                        {inc.priority} {inc.severity.toUpperCase()}
                      </span>
                      <Badge variant={status.variant} className="text-[10px]">{status.label}</Badge>
                    </div>
                    <div className="font-bold text-[15px] text-white">{inc.service}</div>
                    <div className="text-[13px] text-[#8A9BBB] mt-1 truncate">{inc.description}</div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-[11px] text-[#4A5B7A] font-mono">{inc.timestamp}</div>
                    <div className="text-[11px] text-[#8A9BBB] font-mono mt-1">${inc.cost.toFixed(2)} cost</div>
                    <div className="text-[10px] text-[#4A5B7A] font-mono mt-1.5">{inc.id}</div>
                    {!isResolved && (
                      <div className="text-[11px] text-lerna-blue2 font-mono mt-2 flex items-center gap-1 justify-end">
                        View Detail <ArrowRight size={10} />
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}