'use client'
// src/components/ui/index.tsx
import { motion } from 'framer-motion'
import clsx from 'clsx'
import { ReactNode } from 'react'

// ─── Badge ───────────────────────────────────────────────────────────────────
type BadgeVariant = 'green' | 'red' | 'amber' | 'blue' | 'purple' | 'cyan'

const badgeStyles: Record<BadgeVariant, string> = {
  green:  'bg-[rgba(16,185,129,0.15)]  text-lerna-green  border-[rgba(16,185,129,0.25)]',
  red:    'bg-[rgba(239,68,68,0.15)]   text-lerna-red    border-[rgba(239,68,68,0.25)]',
  amber:  'bg-[rgba(245,158,11,0.15)]  text-lerna-amber  border-[rgba(245,158,11,0.25)]',
  blue:   'bg-[rgba(59,130,246,0.15)]  text-lerna-blue2  border-[rgba(59,130,246,0.25)]',
  purple: 'bg-[rgba(168,85,247,0.15)]  text-lerna-purple2 border-[rgba(168,85,247,0.25)]',
  cyan:   'bg-[rgba(6,182,212,0.15)]   text-lerna-cyan   border-[rgba(6,182,212,0.25)]',
}

export function Badge({ variant, children, className }: { variant: BadgeVariant; children: ReactNode; className?: string }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold font-mono tracking-wide border',
      badgeStyles[variant], className
    )}>
      {children}
    </span>
  )
}

// ─── Button ──────────────────────────────────────────────────────────────────
type ButtonVariant = 'primary' | 'outline' | 'danger' | 'ghost'

const buttonStyles: Record<ButtonVariant, string> = {
  primary: 'bg-gradient-to-r from-lerna-blue to-lerna-purple text-white shadow-[0_4px_15px_rgba(59,130,246,0.3)] hover:shadow-[0_6px_20px_rgba(59,130,246,0.4)] hover:-translate-y-0.5',
  outline: 'bg-transparent text-[#8A9BBB] border border-border-2 hover:bg-bg-4 hover:text-white hover:border-lerna-blue',
  danger:  'bg-[rgba(239,68,68,0.15)] text-lerna-red border border-[rgba(239,68,68,0.3)] hover:bg-lerna-red hover:text-white',
  ghost:   'bg-transparent text-[#8A9BBB] hover:text-white hover:bg-bg-4',
}

export function Button({
  variant = 'outline',
  children,
  onClick,
  className,
  type = 'button',
}: {
  variant?: ButtonVariant
  children: ReactNode
  onClick?: () => void
  className?: string
  type?: 'button' | 'submit'
}) {
  return (
    <motion.button
      whileHover={{ scale: variant === 'primary' ? 1.01 : 1 }}
      whileTap={{ scale: 0.97 }}
      type={type}
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold cursor-pointer transition-all duration-150 font-sans',
        buttonStyles[variant],
        className
      )}
    >
      {children}
    </motion.button>
  )
}

// ─── Card ────────────────────────────────────────────────────────────────────
export function Card({ children, className, glow }: { children: ReactNode; className?: string; glow?: 'blue' | 'purple' }) {
  return (
    <div className={clsx(
      'relative bg-bg-2 border border-border rounded-2xl overflow-hidden transition-colors duration-200 hover:border-border-2',
      className
    )}>
      {glow && (
        <div className={clsx(
          'absolute -top-10 -right-10 w-24 h-24 rounded-full blur-3xl',
          glow === 'blue' ? 'bg-[rgba(59,130,246,0.15)]' : 'bg-[rgba(168,85,247,0.15)]'
        )} />
      )}
      {children}
    </div>
  )
}

// ─── SectionTitle ─────────────────────────────────────────────────────────────
export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-3">
      {children}
    </div>
  )
}

// ─── PageHeader ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 className="text-[22px] font-black tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-[#4A5B7A] font-mono mt-1">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2.5 flex-wrap">{children}</div>}
    </div>
  )
}

// ─── StatCard ─────────────────────────────────────────────────────────────────
export function StatCard({
  label,
  value,
  sub,
  valueColor = 'text-white',
  icon,
  iconBg,
  glow,
}: {
  label: string
  value: string
  sub?: string
  valueColor?: string
  icon?: ReactNode
  iconBg?: string
  glow?: 'blue' | 'purple'
}) {
  return (
    <Card glow={glow} className="p-5">
      <div className="text-[11px] font-semibold text-[#4A5B7A] tracking-widest uppercase font-mono mb-2.5">
        {label}
      </div>
      <div className={clsx('text-[32px] font-black tracking-tight leading-none', valueColor)}>
        {value}
      </div>
      {sub && <div className="text-xs text-[#8A9BBB] mt-1.5">{sub}</div>}
      {icon && (
        <div className={clsx('absolute top-4 right-4 w-9 h-9 rounded-xl flex items-center justify-center', iconBg)}>
          {icon}
        </div>
      )}
    </Card>
  )
}