/**
 * API timestamps are typically ISO-8601 in UTC. Display in the browser's locale
 * and local timezone by default, or force a zone with NEXT_PUBLIC_DISPLAY_TIMEZONE
 * (e.g. Asia/Kolkata for IST for every viewer).
 */

function displayTimeZone(): string | undefined {
  const raw = process.env.NEXT_PUBLIC_DISPLAY_TIMEZONE?.trim()
  return raw || undefined
}

function withDisplayTimeZone(base: Intl.DateTimeFormatOptions): Intl.DateTimeFormatOptions {
  const tz = displayTimeZone()
  if (!tz) return base
  return { ...base, timeZone: tz }
}

/** Format an ISO (or parseable) instant for UI: medium date + short time. */
export function formatDateTime(iso: string | null | undefined): string {
  if (iso == null || iso === '') return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString(undefined, withDisplayTimeZone({ dateStyle: 'medium', timeStyle: 'short' }))
}

/** Compact clock string for live UI (e.g. chat message stamps). */
export function formatClockNow(date: Date = new Date()): string {
  return date.toLocaleTimeString(undefined, withDisplayTimeZone({ hour: '2-digit', minute: '2-digit', second: '2-digit' }))
}
