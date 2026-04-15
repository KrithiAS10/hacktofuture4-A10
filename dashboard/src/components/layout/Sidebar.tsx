'use client'
// src/components/layout/Sidebar.tsx
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { LayoutDashboard, AlertTriangle, FileText, Bot, MessageSquare } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { href: '/dashboard', label: 'Dashboard',       icon: LayoutDashboard, badge: null },
  { href: '/incidents', label: 'Incidents',        icon: AlertTriangle,   badge: '3'  },
  { href: '/incidents/INC-2024-0891', label: 'Incident Detail', icon: FileText, badge: null },
  { href: '/agents',   label: 'Agents',            icon: Bot,             badge: null },
  { href: '/chat',     label: 'Chat Panel',        icon: MessageSquare,   badge: null },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 w-[220px] h-screen bg-bg-2 border-r border-border flex flex-col z-50">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-lerna-blue to-lerna-purple flex items-center justify-center text-white font-black text-sm shadow-lg">
          L
        </div>
        <div>
          <div className="gradient-text text-sm font-bold leading-tight">Project Lerna</div>
          <div className="text-[9px] text-[#4A5B7A] font-mono tracking-widest mt-0.5">AUTONOMOUS SRE</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 flex flex-col gap-0.5">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href) && item.href.length > 10)
          const isDashActive = item.href === '/dashboard' && pathname === '/dashboard'
          const active = isActive || isDashActive

          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                whileHover={{ x: 2 }}
                className={clsx(
                  'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 border',
                  active
                    ? 'bg-gradient-to-r from-[rgba(59,130,246,0.15)] to-[rgba(168,85,247,0.1)] text-white border-border-2'
                    : 'text-[#8A9BBB] border-transparent hover:bg-bg-4 hover:text-white hover:border-border'
                )}
              >
                <Icon size={15} className="shrink-0 opacity-80" />
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className="bg-lerna-red text-white text-[10px] px-1.5 py-0.5 rounded-full font-mono leading-none">
                    {item.badge}
                  </span>
                )}
              </motion.div>
            </Link>
          )
        })}
      </nav>

      {/* Bottom status */}
      <div className="px-3 py-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-[#8A9BBB]">
          <span className="w-2 h-2 rounded-full bg-lerna-green shadow-[0_0_6px_#10B981]" />
          All systems operational
        </div>
        <div className="text-[10px] text-[#4A5B7A] font-mono mt-1.5">v2.4.1 · prod-cluster-01</div>
      </div>
    </aside>
  )
}