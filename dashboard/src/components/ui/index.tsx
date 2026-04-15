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
  disabled = false,
}: {
  variant?: ButtonVariant
  children: ReactNode
  onClick?: () => void
  className?: string
  type?: 'button' | 'submit'
  disabled?: boolean
}) {
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : variant === 'primary' ? 1.01 : 1 }}
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      type={type}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={clsx(
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold cursor-pointer transition-all duration-150 font-sans',
        disabled && 'opacity-50 cursor-not-allowed pointer-events-none',
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
    <div
      className={clsx(
        'relative overflow-hidden rounded-xl border border-border bg-bg-2/90 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] transition-colors duration-200 hover:border-border-2',
        className
      )}
    >
      {glow && (
        <div
          className={clsx(
            'pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full blur-3xl',
            glow === 'blue' ? 'bg-[rgba(59,130,246,0.12)]' : 'bg-[rgba(168,85,247,0.12)]'
          )}
        />
      )}
      {children}
    </div>
  )
}

// ─── SectionTitle ─────────────────────────────────────────────────────────────
export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-[#5c6d8c]">
      {children}
    </div>
  )
}

// ─── PageHeader ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/80 pb-6">
      <div className="min-w-0">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-white md:text-[26px]">{title}</h1>
        {subtitle && <p className="mt-1.5 max-w-xl text-[13px] leading-relaxed text-[#8a9bbb]">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
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
      <div className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#5c6d8c]">{label}</div>
      <div className={clsx('text-[26px] font-bold tabular-nums tracking-tight leading-none md:text-[28px]', valueColor)}>
        {value}
      </div>
      {sub && <div className="mt-2 text-[12px] leading-snug text-[#8a9bbb]">{sub}</div>}
      {icon && (
        <div className={clsx('absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-lg', iconBg)}>
          {icon}
        </div>
      )}
    </Card>
  )
}