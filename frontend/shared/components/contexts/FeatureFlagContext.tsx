'use client'
import React, { createContext, useContext, useEffect, useState } from 'react'

interface FeatureFlagContextType {
  features: string[]
  hasFeature: (featureName: string) => boolean
  loading: boolean
}

const FeatureFlagContext = createContext<FeatureFlagContextType>({
  features: [],
  hasFeature: () => false,
  loading: true
})

export function FeatureFlagProvider({ children }: { children: React.ReactNode }) {
  const [features, setFeatures] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchFeatures = async () => {
      try {
        const token = localStorage.getItem('mb_token')
        if (!token) {
          setLoading(false)
          return
        }
        const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'https://maitri-fullstack-1.onrender.com').replace(/\/$/, '')
        const res = await fetch(`${API_URL}/api/features/my-flags`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          setFeatures(data.features || [])
        }
      } catch (err) {
        console.error("Failed to fetch feature flags", err)
      } finally {
        setLoading(false)
      }
    }
    fetchFeatures()
  }, [])

  const hasFeature = (featureName: string) => features.includes(featureName)

  return (
    <FeatureFlagContext.Provider value={{ features, hasFeature, loading }}>
      {children}
    </FeatureFlagContext.Provider>
  )
}

export const useFeatureFlags = () => useContext(FeatureFlagContext)
