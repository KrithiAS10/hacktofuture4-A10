// src/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'
import { AppProviders } from '@/app/providers'
import { Sidebar } from '@/components/layout/Sidebar'

export const metadata: Metadata = {
  title: 'Project Lerna — Autonomous SRE Dashboard',
  description: 'AI-powered site reliability engineering platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-bg text-[#e8edf5]">
        <AppProviders>
          <Sidebar />
          <main className="app-canvas ml-[var(--sidebar-width)] flex-1 min-h-screen">
            <div className="app-canvas-inner">{children}</div>
          </main>
        </AppProviders>
      </body>
    </html>
  )
}