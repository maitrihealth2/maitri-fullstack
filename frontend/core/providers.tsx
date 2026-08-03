'use client'

import { useEffect } from 'react'
import { ThemeProvider } from 'next-themes'
import { FeatureFlagProvider } from '@/shared/components/contexts/FeatureFlagContext'

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'https://maitri-fullstack-1.onrender.com').replace(/\/$/, '')

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Silently wake up the Render backend on app load to avoid cold-start
    // timeouts when the user hits login. Fire-and-forget — errors are ignored.
    fetch(`${API_URL}/health`).catch(() => {})
  }, [])

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <FeatureFlagProvider>
        {children}
      </FeatureFlagProvider>
    </ThemeProvider>
  )
}

