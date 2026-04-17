'use client'
// src/components/layout/Sidebar.tsx
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { LayoutDashboard, AlertTriangle, Bot, MessageSquare, Settings } from 'lucide-react'
import clsx from 'clsx'

import { useWorkflows } from '@/context/WorkflowsContext'

const navItems = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/settings', label: 'Settings', icon: Settings },
] as const

export function Sidebar() {
  const pathname = usePathname()
  const { openCount } = useWorkflows()

  return (
    <aside className="fixed left-0 top-0 z-50 flex h-screen w-[var(--sidebar-width)] flex-col border-r border-border bg-[#0a0e18]/95 backdrop-blur-md">
      <div className="flex items-center gap-3 border-b border-border px-5 py-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-lerna-blue to-[#6366f1] text-sm font-bold text-white shadow-md shadow-lerna-blue/20">
          L
        </div>
        <div className="min-w-0">
          <div className="font-display text-[15px] font-semibold tracking-tight text-white">Lerna</div>
          <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-[#5c6d8c]">
            Operations
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3 py-4">
        {navItems.map((item) => {
          const Icon = item.icon
          const active =
            item.href === '/dashboard'
              ? pathname === item.href
              : pathname === item.href || pathname.startsWith(`${item.href}/`)

          return (
            <Link key={item.href} href={item.href} className="block rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-lerna-blue/50">
              <motion.div
                whileHover={{ x: 1 }}
                transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                className={clsx(
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors',
                  active
                    ? 'bg-bg-4/80 text-white'
                    : 'text-[#8a9bbb] hover:bg-bg-4/40 hover:text-white'
                )}
              >
                {active && (
                  <span
                    className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-lerna-blue shadow-[0_0_12px_rgba(59,130,246,0.6)]"
                    aria-hidden
                  />
                )}
                <Icon
                  size={17}
                  strokeWidth={active ? 2 : 1.75}
                  className={clsx('shrink-0', active ? 'text-lerna-blue2' : 'text-[#6b7c9e] group-hover:text-[#9aaccc]')}
                />
                <span className="flex-1 truncate">{item.label}</span>
                {item.href === '/incidents' && openCount > 0 ? (
                  <span className="rounded-md bg-lerna-red/90 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-white">
                    {openCount}
                  </span>
                ) : null}
              </motion.div>
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-border px-4 py-4">
        <div className="flex items-center gap-2 text-[12px] text-[#8a9bbb]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-lerna-green opacity-40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-lerna-green" />
          </span>
          Connected
        </div>
        <div className="mt-1.5 font-mono text-[10px] text-[#5c6d8c]">v2.4.1 · prod-cluster-01</div>
      </div>
    </aside>
  )
}