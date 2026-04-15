// src/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'

export const metadata: Metadata = {
  title: 'Project Lerna — Autonomous SRE Dashboard',
  description: 'AI-powered site reliability engineering platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-bg text-[#E8EDF5]">
        <Sidebar />
        <main className="ml-[220px] flex-1 min-h-screen">
          {children}
        </main>
      </body>
    </html>
  )
}